"""WP-08 (ampliación de sesión 2026-08-01) — lectura de plantillas de
notificación editables desde `configuracion_sistema` (categoría
`plantilla_notificacion`), con fallback al texto original hardcodeado si
la clave todavía no está sembrada. Mismo patrón que
`app.carrito.services.abandono_service._plantilla`."""

from app.seguridad.repositories.seguridad_repo import SeguridadRepository


async def plantilla(clave: str, default: str) -> str:
    registro = await SeguridadRepository().get_config(clave)
    return registro["valor"] if registro else default
