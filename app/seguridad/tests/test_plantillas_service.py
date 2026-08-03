"""Ampliación de sesión 2026-08-01 — `plantillas_service.plantilla()`,
usado por recuperación de contraseña, reseteo por admin y bienvenida."""

from app.seguridad.services.plantillas_service import plantilla


async def test_plantilla_usa_valor_sembrado():
    valor = await plantilla("bienvenida.plantilla_asunto", "default que no debería usarse")
    assert valor == "Bienvenido a AeroTrack Travel"


async def test_plantilla_usa_fallback_si_clave_no_existe():
    valor = await plantilla("no_existe.clave_inventada", "valor por default")
    assert valor == "valor por default"
