"""WP-04 (auditoría de WorkPanels, 2026-07-31) — listado enriquecido de
reservas para el panel de backoffice: filtros por estado/período/canal/
código/nombre de pasajero, y acciones habilitadas según `estado` (RN-RES-003,
`cancelar_reserva_service.py`) — no hay un editor de estado libre, la reserva
solo se mueve por las acciones de negocio que ya existían.
"""

import datetime

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository

# Reglas ya vigentes en cancelar_reserva_service/modificar_reserva_service y
# detalle_reserva.html — acá solo se reutilizan para decidir qué botón
# mostrar en cada fila del listado, sin duplicar la validación real (el
# service de cancelar sigue siendo la única fuente de verdad).
ESTADOS_CON_VOUCHER = {"confirmada", "modificada", "completada"}
ESTADOS_CANCELABLES = {"pendiente_pago", "confirmada", "modificada"}
# "Iniciar reembolso" y "Cancelar" son el mismo endpoint (cancelar_reserva ya
# reembolsa solo si hubo un pago exitoso) — acá solo se decide la etiqueta.
ESTADOS_CON_REEMBOLSO_AL_CANCELAR = {"confirmada", "modificada"}


def _horas_para_vencer(reserva: dict) -> float | None:
    if reserva.get("estado") != "pendiente_pago" or not reserva.get("fecha_expiracion_pago"):
        return None
    try:
        expira = datetime.datetime.fromisoformat(reserva["fecha_expiracion_pago"].replace("Z", "+00:00"))
    except ValueError:
        return None
    delta = expira - datetime.datetime.now(datetime.timezone.utc)
    return round(delta.total_seconds() / 3600, 1)


async def listar_reservas_backoffice(
    estado: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    canal: str | None = None,
    codigo_reserva: str | None = None,
    nombre_pasajero: str | None = None,
    agente_id: str | None = None,
) -> list[dict]:
    repo = ReservasRepository()
    reservas = await repo.listar_todas(
        estado=estado or None, desde=desde or None, hasta=hasta or None, agente_id=agente_id or None
    )

    if canal:
        reservas = [r for r in reservas if r.get("canal") == canal]
    if codigo_reserva:
        termino_codigo = codigo_reserva.lower()
        reservas = [r for r in reservas if termino_codigo in (r.get("codigo_reserva") or "").lower()]

    pasajeros_repo = PasajerosRepository()
    cache_nombres: dict[str, str] = {}

    async def _nombre_de(pasajero_id: str) -> str:
        if pasajero_id not in cache_nombres:
            pasajero = await pasajeros_repo.obtener_pasajero(pasajero_id)
            usuario = await pasajeros_repo.usuario_por_id(pasajero["usuario_id"]) if pasajero else None
            cache_nombres[pasajero_id] = usuario.get("nombre_completo", "") if usuario else ""
        return cache_nombres[pasajero_id]

    termino_nombre = nombre_pasajero.lower() if nombre_pasajero else None
    filas = []
    for r in reservas:
        nombre = await _nombre_de(r["pasajero_titular_id"])
        if termino_nombre and termino_nombre not in nombre.lower():
            continue
        estado_r = r.get("estado")
        filas.append(
            {
                **r,
                "pasajero_nombre": nombre,
                "horas_para_vencer": _horas_para_vencer(r),
                "puede_cancelar": estado_r in ESTADOS_CANCELABLES,
                "es_reembolso": estado_r in ESTADOS_CON_REEMBOLSO_AL_CANCELAR,
                "tiene_voucher": estado_r in ESTADOS_CON_VOUCHER,
            }
        )
    return filas
