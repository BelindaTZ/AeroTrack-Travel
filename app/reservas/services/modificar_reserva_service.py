"""RF-RES-003 (CU-O23) — modificar reserva. RN-RES-001, RN-RES-002.

El cobro/reembolso de diferencia (CU-O47) se calcula aquí con el monto
exacto y se dispara de verdad contra Facturación
(`diferencia_tarifa_service.cobrar_o_reembolsar_diferencia`, llamada
in-process — mismo patrón que `pago_stub_service.confirmar_pago_reserva`).
"""

from app.facturacion.services.diferencia_tarifa_service import (
    CobroDiferenciaRechazado,
    PagoOriginalNoEncontrado,
    cobrar_o_reembolsar_diferencia,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.shared.pocketbase_client import get_pocketbase_client
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.cupo_service import verificar_y_reservar_cupo

ESTADOS_BLOQUEADOS = {"cancelada", "completada"}


class ReservaNoEncontrada(Exception):
    pass


class SinPermiso(Exception):
    pass


class ReservaBloqueada(Exception):
    pass


class TarifaNoEncontrada(Exception):
    pass


class CupoNoDisponible(Exception):
    pass


def _autorizado(usuario: dict, reserva: dict, pasajero: dict | None) -> bool:
    es_titular = pasajero is not None and reserva["pasajero_titular_id"] == pasajero["id"]
    es_agente_de_la_reserva = reserva.get("agente_id") == usuario["id"]
    es_administrador = usuario.get("tipo_actor") == "administrador"
    return es_titular or es_agente_de_la_reserva or es_administrador


async def modificar_reserva(usuario: dict, reserva_id: str, nueva_tarifa_id: str | None = None) -> dict:
    repo = ReservasRepository()
    vuelos_repo = VuelosRepository()

    reserva = await repo.obtener_reserva(reserva_id)
    if reserva is None:
        raise ReservaNoEncontrada()

    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if not _autorizado(usuario, reserva, pasajero):
        raise SinPermiso()

    if reserva["estado"] in ESTADOS_BLOQUEADOS:
        raise ReservaBloqueada()

    if not nueva_tarifa_id or nueva_tarifa_id == reserva["tarifa_id"]:
        # Nada que cambie vuelo/tarifa -> RN-RES-002: ninguna diferencia que disparar.
        return reserva

    tarifa_actual = await vuelos_repo.obtener_tarifa(reserva["tarifa_id"])
    nueva_tarifa = await vuelos_repo.obtener_tarifa(nueva_tarifa_id)
    if nueva_tarifa is None:
        raise TarifaNoEncontrada()

    # RN-RES-001: revalidar cupo sobre la NUEVA tarifa antes de modificar.
    if not await verificar_y_reservar_cupo(nueva_tarifa_id):
        raise CupoNoDisponible()

    # Libera el cupo de la tarifa anterior — sin esto quedaría "atrapado"
    # (mismo patrón de incremento directo que `expiracion_service`).
    if tarifa_actual is not None:
        client = get_pocketbase_client()
        await client.update_record(
            "tarifas_vuelo",
            tarifa_actual["id"],
            {"cupos_disponibles": tarifa_actual["cupos_disponibles"] + 1},
        )

    diferencia = round(nueva_tarifa["precio_final"] - (tarifa_actual["precio_final"] if tarifa_actual else 0), 2)
    nuevo_total = round(reserva["total_pagar"] + diferencia, 2)

    actualizada = await repo.actualizar_reserva(
        reserva_id,
        {
            "estado": "modificada",
            "vuelo_id": nueva_tarifa["vuelo_id"],
            "tarifa_id": nueva_tarifa_id,
            "total_pagar": nuevo_total,
        },
    )
    # Mantener reserva_items en sincronía con el dual-write de crear_reserva_service.
    item_vuelo = await repo.item_de_reserva_por_tipo(reserva_id, "vuelo")
    if item_vuelo is not None:
        await repo.actualizar_item(
            item_vuelo["id"],
            {
                "vuelo_id": nueva_tarifa["vuelo_id"],
                "tarifa_vuelo_id": nueva_tarifa_id,
                "precio_final": nueva_tarifa["precio_final"],
                "estado_item": "modificado",
            },
        )

    detalle = {"tarifa_anterior": reserva["tarifa_id"], "tarifa_nueva": nueva_tarifa_id}
    if diferencia != 0:
        # RN-RES-002: CU-O47 se dispara SOLO si el precio efectivamente cambió.
        detalle["diferencia_tarifa"] = diferencia
        try:
            resultado = await cobrar_o_reembolsar_diferencia(reserva_id, diferencia)
            detalle["diferencia_tipo"] = resultado["tipo"]
            detalle["diferencia_registro_id"] = resultado.get("id")
        except PagoOriginalNoEncontrado:
            # Reserva aún no pagada (sigue pendiente_pago) — la diferencia ya
            # quedó incluida en el `total_pagar` recién actualizado y se cobra
            # completa en el pago inicial, no como un cargo aparte.
            detalle["diferencia_tipo"] = "incluida_en_pago_inicial"
        except CobroDiferenciaRechazado as exc:
            detalle["diferencia_tipo"] = "cobro_rechazado"
            detalle["diferencia_motivo_rechazo"] = exc.motivo

    await AuditService().insertar(
        "modificar", "reservas", usuario_id=usuario["id"], registro_id=reserva_id, detalle=detalle
    )
    return actualizada
