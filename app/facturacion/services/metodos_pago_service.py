"""WP-18 (auditoría de WorkPanels, 2026-08-01) — CRUD de `metodos_pago`,
antes solo gestionable editando la base o re-corriendo un script de seed."""

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.seguridad.services.audit_service import AuditService


class MetodoPagoInvalido(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def crear_metodo_pago(usuario: dict, data: dict) -> dict:
    repo = FacturacionRepository()
    metodo = await repo.crear_metodo_pago(data)
    await AuditService().insertar(
        "crear_metodo_pago", "metodos_pago", usuario_id=usuario["id"], registro_id=metodo["id"]
    )
    return metodo


async def actualizar_metodo_pago(usuario: dict, metodo_id: str, data: dict) -> dict:
    repo = FacturacionRepository()
    if await repo.obtener_metodo_pago(metodo_id) is None:
        raise MetodoPagoInvalido("Método de pago no encontrado")
    actualizado = await repo.actualizar_metodo_pago(metodo_id, data)
    await AuditService().insertar(
        "actualizar_metodo_pago", "metodos_pago", usuario_id=usuario["id"], registro_id=metodo_id
    )
    return actualizado


async def alternar_activo_metodo_pago(usuario: dict, metodo_id: str) -> dict:
    repo = FacturacionRepository()
    metodo = await repo.obtener_metodo_pago(metodo_id)
    if metodo is None:
        raise MetodoPagoInvalido("Método de pago no encontrado")
    nuevo_activo = not metodo.get("activo", True)

    if not nuevo_activo:
        # `metodo_pago_por_defecto()` (pago_service.py) exige al menos uno
        # activo=true — desactivar el último dejaría todo el flujo de pago
        # roto con un RuntimeError, no un rechazo controlado.
        activos = await repo.listar_metodos_pago(estado="activo")
        if len(activos) <= 1 and any(m["id"] == metodo_id for m in activos):
            raise MetodoPagoInvalido("No se puede desactivar el único método de pago activo")

    actualizado = await repo.actualizar_metodo_pago(metodo_id, {"activo": nuevo_activo})
    await AuditService().insertar(
        "reactivar_metodo_pago" if nuevo_activo else "desactivar_metodo_pago",
        "metodos_pago", usuario_id=usuario["id"], registro_id=metodo_id,
        detalle={"activo": nuevo_activo},
    )
    return actualizado
