"""WP-12 (auditoría de WorkPanels, 2026-07-31) — gestión manual de
disrupciones individuales desde el backoffice de Operaciones. Antes solo
existían transiciones automáticas (`riesgo_service.py`,
`api_estado_vuelo_service.py`, `monitor_correo_service.py`); no había
forma de que un operador corrigiera manualmente una que el sistema dejó
abierta (o resuelta fuera de banda, ej. por contacto directo con la
aerolínea)."""

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.seguridad.services.audit_service import AuditService


class DisrupcionInvalida(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def resolver_disrupcion_manual(usuario: dict, disrupcion_id: str) -> dict:
    repo = DisrupcionesRepository()
    disrupcion = await repo.obtener_disrupcion(disrupcion_id)
    if disrupcion is None:
        raise DisrupcionInvalida("Disrupción no encontrada")
    if disrupcion.get("estado") == "resuelta":
        raise DisrupcionInvalida("Esa disrupción ya estaba resuelta")

    actualizada = await repo.actualizar_disrupcion(disrupcion_id, {"estado": "resuelta"})
    await AuditService().insertar(
        "resolver_disrupcion_manual", "disrupciones", usuario_id=usuario["id"], registro_id=disrupcion_id
    )
    return actualizada
