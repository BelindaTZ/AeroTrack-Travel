"""RF-RES-007 (CU-O44) — expirar reserva pendiente de pago vencida.

**2026-07-19:** la liberación de cupo se generalizó a los 5 tipos de
producto (antes solo tocaba `tarifas_vuelo` directo, y además lo hacía sin
pasar por `cupo_service` — un lock distinto al que usa el decremento real
en `app.shared.cupo_service`, dos mecanismos separados para el mismo dato).
Ahora se recorren los `reserva_items` reales de la reserva (existen para
los 5 tipos desde Reservas 1.4/Carrito) y se libera cupo vía el mismo
servicio compartido que lo reservó — mismo lock, sin condición de carrera
nueva. Antes de esto, una reserva `pendiente_pago` sin `tarifa_id` (creada
por Carrito para un hotel/actividad/crucero) habría reventado esta rutina
completa con un `PocketBaseError` no capturado en `client.get_record(
"tarifas_vuelo", None)` — nunca se llegó a activar en la práctica porque
Carrito tampoco fijaba `fecha_expiracion_pago` (corregido en el mismo
cambio, ver `carrito_service.confirmar_checkout`), pero era un riesgo
latente real.
"""

import datetime

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.services.reserva_locks import locks
from app.seguridad.services.audit_service import AuditService
from app.shared.catalogo_producto import CATALOGO_POR_TIPO
from app.shared.cupo_service import liberar_cupo


async def _liberar_cupo_de_items(repo: ReservasRepository, reserva_id: str) -> None:
    items = await repo.items_de_reserva(reserva_id)
    for item in items:
        info = CATALOGO_POR_TIPO.get(item["tipo_producto"])
        if info is None:
            continue
        coleccion, _, campo_id, campo_cupo = info
        if campo_cupo is None:
            continue
        registro_id = item.get(campo_id)
        if not registro_id:
            continue
        await liberar_cupo(coleccion, registro_id, campo_cupo, int(item.get("cantidad") or 1))


async def expirar_pendientes() -> int:
    repo = ReservasRepository()

    ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    vencidas = await repo.listar_pendientes_vencidas(ahora_iso)

    expiradas = 0
    for reserva in vencidas:
        # Mismo lock por reserva_id que `pago_stub_service` — sin él, un
        # pago concurrente podría confirmar la reserva justo entre esta
        # búsqueda y la cancelación de abajo, y esta rutina la cancelaría
        # igual, perdiendo un pago ya aceptado (RN-RES-005).
        async with locks[reserva["id"]]:
            actual = await repo.obtener_reserva(reserva["id"])
            if actual is None or actual["estado"] != "pendiente_pago":
                continue

            await repo.actualizar_reserva(reserva["id"], {"estado": "cancelada"})
            await _liberar_cupo_de_items(repo, reserva["id"])

            await AuditService().insertar(
                "expirar_reserva",
                "reservas",
                registro_id=reserva["id"],
                detalle={"motivo": "fecha_expiracion_pago_vencida", "cupo_liberado": True},
            )
            expiradas += 1

    return expiradas
