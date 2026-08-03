"""WP-16 (auditoría de WorkPanels, 2026-08-01) — CRUD de `aerolineas`.
Antes no existía ningún camino de código para dar de alta una aerolínea
nueva: solo se leían (búsqueda pública, generación de vuelos, comisiones),
nunca se creaban ni editaban desde el backoffice."""

from app.seguridad.services.audit_service import AuditService
from app.shared.pocketbase_client import PocketBaseError
from app.vuelos.repositories.vuelos_repo import VuelosRepository


class AerolineaInvalida(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def crear_aerolinea(usuario: dict, data: dict) -> dict:
    repo = VuelosRepository()
    aerolinea = await repo.crear_aerolinea(data)
    await AuditService().insertar(
        "crear_aerolinea", "aerolineas", usuario_id=usuario["id"], registro_id=aerolinea["id"]
    )
    return aerolinea


async def actualizar_aerolinea(usuario: dict, aerolinea_id: str, data: dict) -> dict:
    repo = VuelosRepository()
    try:
        aerolinea = await repo.obtener_aerolinea(aerolinea_id)
    except PocketBaseError as exc:
        raise AerolineaInvalida("Aerolínea no encontrada") from exc

    actualizada = await repo.actualizar_aerolinea(aerolinea_id, data)
    await AuditService().insertar(
        "actualizar_aerolinea", "aerolineas", usuario_id=usuario["id"], registro_id=aerolinea_id
    )
    return actualizada


async def alternar_activa_aerolinea(usuario: dict, aerolinea_id: str) -> dict:
    repo = VuelosRepository()
    try:
        aerolinea = await repo.obtener_aerolinea(aerolinea_id)
    except PocketBaseError as exc:
        raise AerolineaInvalida("Aerolínea no encontrada") from exc

    nueva_activa = not aerolinea.get("activa", True)
    actualizada = await repo.actualizar_aerolinea(aerolinea_id, {"activa": nueva_activa})
    await AuditService().insertar(
        "reactivar_aerolinea" if nueva_activa else "desactivar_aerolinea",
        "aerolineas", usuario_id=usuario["id"], registro_id=aerolinea_id,
        detalle={"activa": nueva_activa},
    )
    return actualizada
