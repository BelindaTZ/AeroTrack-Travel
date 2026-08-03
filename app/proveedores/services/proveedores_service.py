"""WP-10 (auditoría de WorkPanels, 2026-07-31)."""

from app.proveedores.repositories.proveedores_repo import ProveedoresRepository
from app.seguridad.services.audit_service import AuditService

TIPOS_PRODUCTO = ("hotel", "auto", "actividad")


class ProveedorInvalido(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def crear_proveedor(usuario: dict, data: dict) -> dict:
    repo = ProveedoresRepository()
    proveedor = await repo.crear(data)
    await AuditService().insertar(
        "crear_proveedor", "proveedores_comerciales", usuario_id=usuario["id"], registro_id=proveedor["id"]
    )
    return proveedor


async def actualizar_proveedor(usuario: dict, proveedor_id: str, data: dict) -> dict:
    repo = ProveedoresRepository()
    proveedor = await repo.obtener(proveedor_id)
    if proveedor is None:
        raise ProveedorInvalido("Proveedor no encontrado")
    actualizado = await repo.actualizar(proveedor_id, data)
    await AuditService().insertar(
        "actualizar_proveedor", "proveedores_comerciales", usuario_id=usuario["id"], registro_id=proveedor_id
    )
    return actualizado


async def alternar_activo_proveedor(usuario: dict, proveedor_id: str) -> dict:
    repo = ProveedoresRepository()
    proveedor = await repo.obtener(proveedor_id)
    if proveedor is None:
        raise ProveedorInvalido("Proveedor no encontrado")

    nuevo_activo = not proveedor.get("activo", True)
    actualizado = await repo.actualizar(proveedor_id, {"activo": nuevo_activo})
    await AuditService().insertar(
        "reactivar_proveedor" if nuevo_activo else "desactivar_proveedor",
        "proveedores_comerciales", usuario_id=usuario["id"], registro_id=proveedor_id,
        detalle={"activo": nuevo_activo},
    )
    return actualizado
