"""RF-INT-002 (CU-T38) — bitácora de sincronizaciones de catálogos externos."""

from fastapi import APIRouter, Depends, Query, Request

from app.integraciones.services.integraciones_service import listar_bitacora, listar_fuentes_con_cuota
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.csv_export import csv_response
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/integraciones")

ESTADOS_CORRIDA = ["exitoso", "parcial", "fallido"]


async def _bitacora_filtrada(
    fuente_id: str | None, desde: str | None, hasta: str | None, estado: str | None
) -> list[dict]:
    corridas = await listar_bitacora(fuente_id=fuente_id, desde=desde, hasta=hasta, estado=estado)
    fuentes = await listar_fuentes_con_cuota()
    nombre_por_id = {f["id"]: f["nombre"] for f in fuentes}
    corridas_out = [{**c, "fuente_nombre": nombre_por_id.get(c["fuente_id"], "")} for c in corridas]
    return corridas_out, fuentes


@router.get("/bitacora")
async def ver_bitacora(
    request: Request,
    fuente_id: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    estado: str | None = None,
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("integraciones", "ver", "sincronizaciones_log")),
):
    corridas_out, fuentes = await _bitacora_filtrada(fuente_id, desde, hasta, estado)
    pagina = paginar(corridas_out, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "fuentes": fuentes,
            "estados": ESTADOS_CORRIDA,
            "filtros": {
                "fuente_id": fuente_id or "", "desde": desde or "", "hasta": hasta or "", "estado": estado or "",
            },
        }
    )
    return templates.TemplateResponse(request, "backoffice/bitacora.html", contexto)


@router.get("/bitacora/exportar")
async def exportar_bitacora(
    fuente_id: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    estado: str | None = None,
    usuario: dict = Depends(requiere_permiso("integraciones", "ver", "sincronizaciones_log")),
):
    corridas_out, _fuentes = await _bitacora_filtrada(fuente_id, desde, hasta, estado)
    return csv_response(
        corridas_out,
        [
            ("fecha_inicio", lambda c: c.get("fecha_inicio", "")),
            ("fuente", lambda c: c["fuente_nombre"]),
            ("tipo_producto", lambda c: c.get("tipo_producto", "")),
            ("estado", lambda c: c.get("estado", "")),
            ("registros_procesados", lambda c: c.get("registros_procesados", 0)),
            ("registros_nuevos", lambda c: c.get("registros_nuevos", 0)),
            ("registros_actualizados", lambda c: c.get("registros_actualizados", 0)),
            ("unidades_cuota_consumidas", lambda c: c.get("unidades_cuota_consumidas", "")),
        ],
        "bitacora_sincronizaciones.csv",
    )
