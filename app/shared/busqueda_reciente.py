"""RN-CTA-001 (Cuenta/Mis Viajes) — cada módulo de producto es responsable
de registrar sus propias búsquedas en `busquedas_recientes`; Cuenta/Mis
Viajes solo lee y relanza, nunca escribe. Vive en `shared` (no en
`app.cuenta`) para que los 5 buscadores lo llamen sin crear una dependencia
circular hacia el módulo que los consume.

`busquedas_recientes` es OPERACIONAL — migrada a MinIO (ver plan de
migración)."""

from datetime import datetime, timezone

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc


async def registrar_busqueda_reciente(usuario: dict | None, tipo_producto: str, criterios: dict) -> None:
    """No-op silencioso si no hay sesión de pasajero — una búsqueda anónima
    o de agente/administrador no tiene "Mis Viajes" donde relanzarse."""
    if not usuario or usuario.get("tipo_actor") != "pasajero":
        return
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        return
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    id_ = moc.generar_id()
    await moc.crear(
        "busquedas_recientes",
        id_,
        {
            "id": id_,
            "created": ahora,
            "updated": ahora,
            "pasajero_id": pasajero["id"],
            "tipo_producto": tipo_producto,
            "criterios": criterios,
            "fecha": ahora,
        },
    )
