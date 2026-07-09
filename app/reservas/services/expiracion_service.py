"""RF-RES-007 (CU-O44) — expirar reserva pendiente de pago vencida.

Único caso de este módulo que incrementa `tarifas_vuelo.cupos_disponibles`
directamente (no vía `cupo_service`, que solo expone verificación+decremento
atómico): liberar cupo es la operación inversa, no tiene condición de
carrera que proteger del mismo modo (dos expiraciones concurrentes sobre la
misma reserva no pueden "liberar de más" porque la segunda ya no encuentra
la reserva en `pendiente_pago` — el filtro de búsqueda actúa como guarda).
"""

import datetime

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.services.reserva_locks import locks
from app.seguridad.services.audit_service import AuditService
from app.shared.pocketbase_client import get_pocketbase_client


async def expirar_pendientes() -> int:
    repo = ReservasRepository()
    client = get_pocketbase_client()

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

            tarifa = await client.get_record("tarifas_vuelo", reserva["tarifa_id"])
            await client.update_record(
                "tarifas_vuelo",
                reserva["tarifa_id"],
                {"cupos_disponibles": tarifa["cupos_disponibles"] + 1},
            )

            await AuditService().insertar(
                "expirar_reserva",
                "reservas",
                registro_id=reserva["id"],
                detalle={"motivo": "fecha_expiracion_pago_vencida", "cupo_liberado": True},
            )
            expiradas += 1

    return expiradas
