"""RF-RES-004 (CU-O24) — cancelar reserva. RN-RES-003.

El reembolso (CU-O37, `<<extend>>` de CU-O24) se calcula aquí con el monto
exacto según la política de la tarifa y se dispara de verdad contra
Facturación (`reembolso_service.procesar_reembolso`, llamada in-process —
mismo patrón que `pago_stub_service.confirmar_pago_reserva`).
"""

from app.facturacion.services.reembolso_service import (
    PagoNoEncontrado,
    ReembolsoNoAplicable,
    procesar_reembolso,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.vuelos.repositories.vuelos_repo import VuelosRepository


class ReservaNoEncontrada(Exception):
    pass


class SinPermiso(Exception):
    pass


class VueloYaCompletado(Exception):
    pass


def _autorizado(usuario: dict, reserva: dict, pasajero: dict | None) -> bool:
    es_titular = pasajero is not None and reserva["pasajero_titular_id"] == pasajero["id"]
    es_agente_de_la_reserva = reserva.get("agente_id") == usuario["id"]
    es_administrador = usuario.get("tipo_actor") == "administrador"
    return es_titular or es_agente_de_la_reserva or es_administrador


async def cancelar_reserva(usuario: dict, reserva_id: str) -> dict:
    repo = ReservasRepository()
    vuelos_repo = VuelosRepository()

    reserva = await repo.obtener_reserva(reserva_id)
    if reserva is None:
        raise ReservaNoEncontrada()

    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if not _autorizado(usuario, reserva, pasajero):
        raise SinPermiso()

    vuelo = await vuelos_repo.obtener_vuelo(reserva["vuelo_id"])
    if vuelo is not None and vuelo["estado"] == "completado":
        # RN-RES-003 — mensaje exacto de la fuente (RF-RES-004).
        raise VueloYaCompletado()

    actualizada = await repo.actualizar_reserva(reserva_id, {"estado": "cancelada"})

    detalle = {"estado_anterior": reserva["estado"]}
    tarifa = await vuelos_repo.obtener_tarifa(reserva["tarifa_id"])
    if tarifa is not None:
        nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
        politica = await vuelos_repo.politica_reembolso(nivel["politica_reembolso_id"])
        if politica["porcentaje_reembolso"] > 0:
            try:
                reembolso = await procesar_reembolso(reserva_id, "Cancelación de reserva")
                detalle["reembolso_monto"] = reembolso["monto"]
                detalle["reembolso_id"] = reembolso["id"]
            except PagoNoEncontrado:
                # Reserva pendiente_pago o sin pago exitoso registrado -> nada que reembolsar.
                detalle["estado_reembolso"] = "sin_pago_que_reembolsar"
            except ReembolsoNoAplicable:
                detalle["estado_reembolso"] = "politica_no_permite_reembolso"

    await AuditService().insertar(
        "cancelar", "reservas", usuario_id=usuario["id"], registro_id=reserva_id, detalle=detalle
    )
    return actualizada
