"""RF-INT-002 (CU-T38) — bitácora de sincronizaciones de catálogos externos."""

from fastapi import APIRouter, Depends, Request

from app.integraciones.services.integraciones_service import listar_bitacora, listar_fuentes_con_cuota
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/integraciones")


@router.get("/bitacora")
async def ver_bitacora(
    request: Request,
    fuente_id: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    usuario: dict = Depends(requiere_permiso("integraciones", "ver", "sincronizaciones_log")),
):
    corridas = await listar_bitacora(fuente_id=fuente_id, desde=desde, hasta=hasta)
    fuentes = await listar_fuentes_con_cuota()
    nombre_por_id = {f["id"]: f["nombre"] for f in fuentes}
    corridas_out = [{**c, "fuente_nombre": nombre_por_id.get(c["fuente_id"], "")} for c in corridas]

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "corridas": corridas_out,
            "fuentes": fuentes,
            "filtros": {"fuente_id": fuente_id or "", "desde": desde or "", "hasta": hasta or ""},
        }
    )
    return templates.TemplateResponse(request, "backoffice/bitacora.html", contexto)
