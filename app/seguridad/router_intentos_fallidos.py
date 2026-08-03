"""RF-SEG-T01 (Táctico) — dashboard de intentos de login fallidos."""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.intentos_fallidos_service import (
    UMBRAL_SOSPECHOSO_DEFAULT,
    VENTANA_HORAS_DEFAULT,
    CuentaNoEncontrada,
    desactivar_cuenta_por_email,
    resumen_intentos_fallidos,
)
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/admin/seguridad")


@router.get("/intentos-fallidos")
async def intentos_fallidos(
    request: Request,
    horas: int = Query(VENTANA_HORAS_DEFAULT, ge=1, le=720),
    usuario: dict = Depends(requiere_permiso("seguridad", "ver", "auditoria")),
):
    # WP-08 (ampliación de sesión 2026-08-01) — umbral editable desde
    # Configuración del sistema; UMBRAL_SOSPECHOSO_DEFAULT sigue siendo el
    # fallback si la clave todavía no está sembrada.
    config_umbral = await SeguridadRepository().get_config("seguridad.intentos_sospechoso_umbral")
    umbral_sospechoso = int(config_umbral["valor"]) if config_umbral else UMBRAL_SOSPECHOSO_DEFAULT

    filas = await resumen_intentos_fallidos(horas=horas, umbral_sospechoso=umbral_sospechoso)
    contexto = await nav_context(usuario)
    contexto.update(
        {
            "filas": filas,
            "horas": horas,
            "umbral_sospechoso": umbral_sospechoso,
            "total_sospechosos": sum(1 for f in filas if f["sospechoso"]),
        }
    )
    return templates.TemplateResponse(request, "admin/intentos_fallidos.html", contexto)


@router.post("/desactivar-cuenta")
async def desactivar_cuenta(
    email: str = Form(...),
    horas: int = Form(VENTANA_HORAS_DEFAULT),
    usuario: dict = Depends(requiere_permiso("seguridad", "editar", "usuarios")),
):
    try:
        await desactivar_cuenta_por_email(usuario, email)
        mensaje = "Cuenta+desactivada"
    except CuentaNoEncontrada:
        mensaje = "No+se+encontró+esa+cuenta"
    return RedirectResponse(
        f"/admin/seguridad/intentos-fallidos?horas={horas}&mensaje={mensaje}", status_code=303
    )
