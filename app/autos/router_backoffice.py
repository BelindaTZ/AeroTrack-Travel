"""CU-T11 — reporte de reservas de autos por proveedor/categoría. Actor:
Administrador (mismo criterio que Ofertas Táctico — sin rol Agente)."""

from fastapi import APIRouter, Depends, Request

from app.autos.services.reporte_service import DIAS_DEFAULT, reporte_por_proveedor_categoria
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/autos")


@router.get("/reporte")
async def reporte(
    request: Request,
    dias: int = DIAS_DEFAULT,
    usuario: dict = Depends(requiere_permiso("autos", "ver")),
):
    filas = await reporte_por_proveedor_categoria(dias)
    contexto = await nav_context(usuario)
    contexto.update({"reporte": filas, "dias": dias})
    return templates.TemplateResponse(request, "backoffice/reporte.html", contexto)
