"""RF-FAC-001 (CU-O32) — procesar pago de reserva. RNF-FAC-001/002.

Fase 2 añade el disparo automático de factura/comisión sobre todo pago
exitoso (`<<include>>` CU-O33/O34) — ver el final de `procesar_pago`.
"""

import datetime

from app.facturacion.integrations.payment_gateway import (
    PAYMENT_METHOD_EXITOSO,
    PAYMENT_METHOD_RECHAZADO,
    cobrar,
)
from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.services.comision_service import registrar_comision
from app.facturacion.services.factura_service import emitir_factura
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.services.pago_stub_service import confirmar_pago_reserva
from app.seguridad.services.audit_service import AuditService
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


def _autorizado(usuario: dict, reserva: dict, pasajero: dict | None) -> bool:
    es_titular = pasajero is not None and reserva["pasajero_titular_id"] == pasajero["id"]
    es_agente = reserva.get("agente_id") == usuario["id"]
    es_administrador = usuario.get("tipo_actor") == "administrador"
    return es_titular or es_agente or es_administrador


async def procesar_pago(usuario: dict, reserva_id: str, escenario: str = "exitoso") -> dict:
    reservas_repo = ReservasRepository()
    facturacion_repo = FacturacionRepository()

    reserva = await reservas_repo.obtener_reserva(reserva_id)
    if reserva is None:
        raise ReservaNoEncontrada()

    pasajero = await reservas_repo.pasajero_de_usuario(usuario["id"])
    if not _autorizado(usuario, reserva, pasajero):
        raise SinPermiso()

    # RNF-FAC-002: idempotencia de aplicación — si ya hay un pago exitoso
    # para esta reserva, no se vuelve a llamar a Stripe en absoluto.
    existente = await facturacion_repo.pago_exitoso_de_reserva(reserva_id)
    if existente is not None:
        return existente

    if reserva["estado"] != "pendiente_pago":
        raise ReservaNoPagable()

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
    # (<<include>> CU-O33/O34 — RF-FAC-002/003).
    vuelo = await VuelosRepository().obtener_vuelo(reserva["vuelo_id"])
    await emitir_factura(reserva, pago)
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
