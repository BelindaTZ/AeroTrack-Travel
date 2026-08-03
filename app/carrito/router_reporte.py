"""CU-T27 — reporte de carritos abandonados y tasa de recuperación por
período. Actor: Administrador."""

from fastapi import APIRouter, Depends, Request

from app.carrito.services.reporte_abandono_service import DIAS_DEFAULT, reporte_recuperacion
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/carrito")


@router.get("/reporte")
async def reporte(
    request: Request,
    dias: int = DIAS_DEFAULT,
    usuario: dict = Depends(requiere_permiso("carrito", "ver")),
):
    datos = await reporte_recuperacion(dias)
    contexto = await nav_context(usuario)
    contexto.update(datos)
    contexto["dias"] = dias
    return templates.TemplateResponse(request, "backoffice/reporte_abandono.html", contexto)
