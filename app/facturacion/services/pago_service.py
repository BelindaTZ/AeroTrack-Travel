"""RF-FAC-001 (CU-O32) — procesar pago de reserva. RNF-FAC-001/002.

Fase 2 añade el disparo automático de factura/comisión sobre todo pago
exitoso (`<<include>>` CU-O33/O34) — ver el final de `procesar_pago`.

RF-FAC-012 (CU-O86) añade el flujo Stripe authorize-then-capture para
"Reservar hotel sin pagar ahora" (RF-HOT-009, CU-O60): cuando algún
`reserva_items` de la reserva tiene `modalidad_pago = pago_diferido`,
`procesar_pago` autoriza en vez de cobrar de inmediato (`_autorizar_pago`)
— la reserva se confirma igual (RF-HOT-009 lo exige explícitamente), pero
factura/voucher/comisión esperan a `capturar_pago_diferido`, porque
CU-O33 los ata a un pago "exitoso", no a uno solo "autorizado"."""

import datetime

from app.facturacion.integrations.payment_gateway import (
    PAYMENT_METHOD_EXITOSO,
    PAYMENT_METHOD_RECHAZADO,
    autorizar,
    capturar,
    cobrar,
)
from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.services.comision_service import registrar_comision
from app.facturacion.services.factura_service import emitir_factura
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.services.pago_stub_service import confirmar_pago_reserva
from app.reservas.services.voucher_service import emitir_voucher
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import tiene_permiso
from app.vuelos.repositories.vuelos_repo import VuelosRepository

ESCENARIOS_PRUEBA = {"exitoso": PAYMENT_METHOD_EXITOSO, "rechazado": PAYMENT_METHOD_RECHAZADO}


class ReservaNoEncontrada(Exception):
    pass


class SinPermiso(Exception):
    pass


class ReservaNoPagable(Exception):
    pass


class PagoRechazadoPorStripe(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


class PagoNoEncontrado(Exception):
    pass


class PagoNoAutorizado(Exception):
    pass


def _ahora_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


async def _stripe_habilitado(facturacion_repo: FacturacionRepository) -> bool:
    """WP-08 (ampliación de sesión 2026-08-01) — feature flag real: si está
    en false, ningún pago/autorización/captura llega a Stripe."""
    config = await facturacion_repo.config("pagos.stripe_habilitado")
    if config is None:
        return True
    return config["valor"].strip().lower() != "false"


async def _autorizado(usuario: dict, reserva: dict, pasajero: dict | None) -> bool:
    es_titular = pasajero is not None and reserva["pasajero_titular_id"] == pasajero["id"]
    es_agente = reserva.get("agente_id") == usuario["id"]
    if es_titular or es_agente:
        return True
    return await tiene_permiso(usuario, "facturacion", "eliminar")


async def procesar_pago(usuario: dict, reserva_id: str, escenario: str = "exitoso") -> dict:
    reservas_repo = ReservasRepository()
    facturacion_repo = FacturacionRepository()

    reserva = await reservas_repo.obtener_reserva(reserva_id)
    if reserva is None:
        raise ReservaNoEncontrada()

    pasajero = await reservas_repo.pasajero_de_usuario(usuario["id"])
    if not await _autorizado(usuario, reserva, pasajero):
        raise SinPermiso()

    # RNF-FAC-002: idempotencia de aplicación — si ya hay un pago exitoso O
    # autorizado (RF-FAC-012, esperando captura) para esta reserva, no se
    # vuelve a llamar a Stripe en absoluto.
    existente = await facturacion_repo.pago_activo_de_reserva(reserva_id)
    if existente is not None:
        return existente

    if reserva["estado"] != "pendiente_pago":
        raise ReservaNoPagable()

    if not await _stripe_habilitado(facturacion_repo):
        raise PagoRechazadoPorStripe("Pagos temporalmente deshabilitados. Intenta más tarde.")

    # RF-HOT-009/RF-FAC-012 (CU-O60/O86): un ítem "pago_diferido" desvía a
    # authorize-then-capture — el resto de esta función es el cobro
    # inmediato estándar (RF-FAC-001).
    items = await reservas_repo.items_de_reserva(reserva_id)
    if any(item.get("modalidad_pago") == "pago_diferido" for item in items):
        return await _autorizar_pago(usuario, reserva, escenario)

    metodo = await facturacion_repo.metodo_pago_por_defecto()
    metodo_stripe_id = ESCENARIOS_PRUEBA.get(escenario, PAYMENT_METHOD_EXITOSO)

    resultado = await cobrar(
        reserva["total_pagar"],
        metodo_stripe_id,
        idempotency_key=f"reserva-{reserva_id}",
        descripcion=f"Reserva {reserva['codigo_reserva']} — AeroTrack Travel",
    )

    if resultado["status"] != "succeeded":
        pago = await facturacion_repo.crear_pago(
            {
                "reserva_id": reserva_id,
                "monto": reserva["total_pagar"],
                "moneda": "USD",
                "metodo_pago_id": metodo["id"],
                "stripe_payment_intent_id": resultado.get("id") or "",
                "estado": "fallido",
            }
        )
        await AuditService().insertar(
            "pago_fallido",
            "pagos",
            usuario_id=usuario["id"],
            registro_id=pago["id"],
            detalle={"motivo": resultado.get("motivo", "Pago rechazado")},
        )
        raise PagoRechazadoPorStripe(resultado.get("motivo", "Pago rechazado"))

    ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    pago = await facturacion_repo.crear_pago(
        {
            "reserva_id": reserva_id,
            "monto": reserva["total_pagar"],
            "moneda": "USD",
            "metodo_pago_id": metodo["id"],
            "stripe_payment_intent_id": resultado["id"],
            "estado": "exitoso",
            "fecha_pago": ahora_iso,
        }
    )

    # Cierra el punto de integración real con Reservas (RN-RES-005): la
    # reserva pasa a confirmada usando la misma lógica ya probada allá,
    # no una reimplementación aquí.
    await confirmar_pago_reserva(reserva_id)

    # Todo pago exitoso deja factura y comisión reales, sin pasos manuales
    # (<<include>> CU-O33/O34 — RF-FAC-002/003). `vuelo_id` es "" (no None)
    # en una reserva sin vuelo (hotel/auto/actividad/crucero) — `get_record`
    # con id vacío pega contra el endpoint de LISTAR, no 404ea, así que hay
    # que filtrar el vacío explícitamente antes de llamarlo (RN-FAC-007
    # ya asume que no todas las reservas tienen vuelo).
    vuelo = await VuelosRepository().obtener_vuelo(reserva["vuelo_id"]) if reserva.get("vuelo_id") else None
    await emitir_factura(reserva, pago)
    await emitir_voucher(reserva)
    if vuelo is not None:
        await registrar_comision(reserva, vuelo, pago)

    await AuditService().insertar(
        "pago_exitoso",
        "pagos",
        usuario_id=usuario["id"],
        registro_id=pago["id"],
        detalle={"stripe_payment_intent_id": resultado["id"]},
    )

    return pago


async def _autorizar_pago(usuario: dict, reserva: dict, escenario: str = "exitoso") -> dict:
    """RF-FAC-012 (CU-O86) — mitad "authorize" del flujo: retiene el cargo
    en Stripe sin capturarlo. La reserva se confirma igual que un pago
    inmediato exitoso (RF-HOT-009 lo exige explícitamente), pero factura/
    voucher/comisión NO se emiten aquí — CU-O33 los ata a un pago
    `exitoso`, y este todavía queda `autorizado` hasta `capturar_pago_diferido`."""
    facturacion_repo = FacturacionRepository()
    metodo = await facturacion_repo.metodo_pago_por_defecto()
    metodo_stripe_id = ESCENARIOS_PRUEBA.get(escenario, PAYMENT_METHOD_EXITOSO)

    resultado = await autorizar(
        reserva["total_pagar"],
        metodo_stripe_id,
        idempotency_key=f"reserva-{reserva['id']}-autorizacion",
        descripcion=f"Reserva {reserva['codigo_reserva']} — AeroTrack Travel (pago diferido)",
    )

    if resultado["status"] != "requires_capture":
        pago = await facturacion_repo.crear_pago(
            {
                "reserva_id": reserva["id"],
                "monto": reserva["total_pagar"],
                "moneda": "USD",
                "metodo_pago_id": metodo["id"],
                "stripe_payment_intent_id": resultado.get("id") or "",
                "estado": "fallido",
                "captura_diferida": True,
            }
        )
        await AuditService().insertar(
            "pago_fallido",
            "pagos",
            usuario_id=usuario["id"],
            registro_id=pago["id"],
            detalle={"motivo": resultado.get("motivo", "Autorización rechazada")},
        )
        raise PagoRechazadoPorStripe(resultado.get("motivo", "Autorización rechazada"))

    pago = await facturacion_repo.crear_pago(
        {
            "reserva_id": reserva["id"],
            "monto": reserva["total_pagar"],
            "moneda": "USD",
            "metodo_pago_id": metodo["id"],
            "stripe_payment_intent_id": resultado["id"],
            "estado": "autorizado",
            "captura_diferida": True,
            "fecha_autorizacion": _ahora_iso(),
        }
    )

    await confirmar_pago_reserva(reserva["id"])

    await AuditService().insertar(
        "pago_autorizado",
        "pagos",
        usuario_id=usuario["id"],
        registro_id=pago["id"],
        detalle={"stripe_payment_intent_id": resultado["id"]},
    )

    return pago


async def capturar_pago_diferido(pago_id: str) -> dict:
    """RF-FAC-012 (CU-O86) — completa el cobro cuando el hotel confirma la
    disponibilidad. HotelLens es de solo lectura (sin API de reserva real,
    ver `hoteles-spec.md`), así que no hay una señal externa real que
    confirme la disponibilidad — se dispara manualmente desde el
    backoffice de Facturación, mismo criterio que CU-O48 ("Forzar estado",
    demo) para acciones sin fuente externa real detrás."""
    facturacion_repo = FacturacionRepository()
    reservas_repo = ReservasRepository()

    pago = await facturacion_repo.obtener_pago(pago_id)
    if pago is None:
        raise PagoNoEncontrado()
    if pago["estado"] != "autorizado":
        raise PagoNoAutorizado()

    if not await _stripe_habilitado(facturacion_repo):
        raise PagoRechazadoPorStripe("Pagos temporalmente deshabilitados. Intenta más tarde.")

    resultado = await capturar(pago["stripe_payment_intent_id"])
    if resultado["status"] != "succeeded":
        raise PagoRechazadoPorStripe(resultado.get("motivo", "Captura rechazada"))

    pago_actualizado = await facturacion_repo.actualizar_pago(
        pago_id, {"estado": "exitoso", "fecha_pago": _ahora_iso()}
    )

    # Recién ahora se cumple CU-O33/O34 (factura/comisión atadas a un pago
    # `exitoso`) y se emite el voucher — mismo tramo final que un pago
    # inmediato exitoso en `procesar_pago`.
    reserva = await reservas_repo.obtener_reserva(pago["reserva_id"])
    if reserva is not None:
        vuelo = await VuelosRepository().obtener_vuelo(reserva["vuelo_id"]) if reserva.get("vuelo_id") else None
        await emitir_factura(reserva, pago_actualizado)
        await emitir_voucher(reserva)
        if vuelo is not None:
            await registrar_comision(reserva, vuelo, pago_actualizado)

    await AuditService().insertar(
        "pago_capturado",
        "pagos",
        registro_id=pago_id,
        detalle={"stripe_payment_intent_id": pago["stripe_payment_intent_id"]},
    )

    return pago_actualizado
