"""RF-SEG-015,016 — ver/filtrar/exportar log de auditoría."""

import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/admin/auditoria")


def _construir_filtro(
    usuario_id: str | None, accion: str | None, tabla: str | None, desde: str | None, hasta: str | None
) -> str | None:
    condiciones = []
    if usuario_id:
        condiciones.append(f'usuario_id="{usuario_id}"')
    if accion:
        condiciones.append(f'accion="{accion}"')
    if tabla:
        condiciones.append(f'tabla="{tabla}"')
    if desde:
        condiciones.append(f'created >= "{desde}"')
    if hasta:
        condiciones.append(f'created <= "{hasta}"')
    return " && ".join(condiciones) if condiciones else None


@router.get("")
async def listar(
    request: Request,
    usuario_id: str | None = None,
    accion: str | None = None,
    tabla: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    usuario: dict = Depends(requiere_permiso("seguridad", "ver", "auditoria")),
):
    repo = SeguridadRepository()
    filtro = _construir_filtro(usuario_id, accion, tabla, desde, hasta)
    resultado = await repo.list_auditoria(filtro=filtro, per_page=100)
    contexto = await nav_context(usuario)
    contexto.update({
        "registros": resultado["items"],
        "filtros": {
            "usuario_id": usuario_id or "",
            "accion": accion or "",
            "tabla": tabla or "",
            "desde": desde or "",
            "hasta": hasta or "",
        },
    })
    return templates.TemplateResponse(request, "admin/auditoria.html", contexto)


@router.get("/exportar")
async def exportar(
    usuario_id: str | None = None,
    accion: str | None = None,
    tabla: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    # No existe acción "exportar" en el catálogo de permisos sembrado para el
    # módulo "seguridad" (solo ver/crear/editar/eliminar) — exportar se gatea
    # con el mismo permiso "ver" que la vista, ya que es una proyección de la
    # misma consulta filtrada, no una acción de mutación distinta.
    usuario: dict = Depends(requiere_permiso("seguridad", "ver", "auditoria")),
):
    repo = SeguridadRepository()
    filtro = _construir_filtro(usuario_id, accion, tabla, desde, hasta)
    resultado = await repo.list_auditoria(filtro=filtro, per_page=500)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["fecha", "usuario_id", "accion", "tabla", "registro_id", "ip", "detalle"])
    for r in resultado["items"]:
        writer.writerow(
            [r["created"], r.get("usuario_id", ""), r["accion"], r["tabla"], r.get("registro_id", ""), r.get("ip", ""), r.get("detalle", "")]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=auditoria.csv"},
    )
