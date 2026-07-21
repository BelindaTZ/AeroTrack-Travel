"""CU-T33 (reporte de consultas), CU-T34 (configurar tono/temas/
respuestas predefinidas) — Actor: Administrador únicamente."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.asistente_ia.services.asistente_service import (
    actualizar_configuracion,
    obtener_configuracion,
    reporte_consultas,
)
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/asistente")


async def _rbac_ver(usuario: dict = Depends(requiere_permiso("asistente_ia", "ver"))):
    return usuario


async def _rbac_editar(usuario: dict = Depends(requiere_permiso("asistente_ia", "editar"))):
    return usuario


@router.get("/configuracion")
async def ver_configuracion(request: Request, usuario: dict = Depends(_rbac_ver)):
    config = await obtener_configuracion()
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(request, "backoffice/configuracion.html", {**contexto, "config": config})


@router.post("/configuracion")
async def guardar_configuracion(
    tono: str = Form(...),
    temas_permitidos: str = Form(""),
    respuestas_clave: list[str] = Form([]),
    respuestas_valor: list[str] = Form([]),
    usuario: dict = Depends(_rbac_editar),
):
    temas = [t.strip() for t in temas_permitidos.split(",") if t.strip()]
    predefinidas = {
        clave.strip(): valor.strip()
        for clave, valor in zip(respuestas_clave, respuestas_valor)
        if clave.strip() and valor.strip()
    }
    await actualizar_configuracion(usuario, tono, temas, predefinidas)
    return RedirectResponse("/backoffice/asistente/configuracion?mensaje=Configuración guardada", status_code=303)


@router.get("/reporte")
async def reporte(request: Request, dias: int = 90, usuario: dict = Depends(_rbac_ver)):
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S.000Z")
    datos = await reporte_consultas(desde)
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(request, "backoffice/reporte.html", {**contexto, "reporte": datos, "dias": dias})
