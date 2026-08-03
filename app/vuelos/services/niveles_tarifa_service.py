"""WP-18 (auditoría de WorkPanels, 2026-08-01) — CRUD de `niveles_tarifa`.
Sin acción de desactivar: no tiene campo `activo` en el esquema y está
referenciado por `tarifas_vuelo` — es un catálogo de configuración, no
transaccional (Crear/Ver/Editar según lo definido en priorización)."""

from app.seguridad.services.audit_service import AuditService
from app.vuelos.repositories.vuelos_repo import VuelosRepository


class NivelTarifaInvalido(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def crear_nivel_tarifa(usuario: dict, data: dict) -> dict:
    repo = VuelosRepository()
    nivel = await repo.crear_nivel_tarifa(data)
    await AuditService().insertar(
        "crear_nivel_tarifa", "niveles_tarifa", usuario_id=usuario["id"], registro_id=nivel["id"]
    )
    return nivel


async def actualizar_nivel_tarifa(usuario: dict, nivel_id: str, data: dict) -> dict:
    repo = VuelosRepository()
    if await repo.obtener_nivel_tarifa(nivel_id) is None:
        raise NivelTarifaInvalido("Nivel de tarifa no encontrado")
    actualizado = await repo.actualizar_nivel_tarifa(nivel_id, data)
    await AuditService().insertar(
        "actualizar_nivel_tarifa", "niveles_tarifa", usuario_id=usuario["id"], registro_id=nivel_id
    )
    return actualizado
