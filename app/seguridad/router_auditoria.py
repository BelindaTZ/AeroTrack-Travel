"""RF-SEG-015,016 — ver/filtrar/exportar log de auditoría."""

from fastapi import APIRouter, Depends, Query, Request

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.csv_export import csv_response
from app.shared.nav import nav_context
from app.shared.paginacion import Pagina
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


async def _resolver_actor_id(actor_email: str | None) -> str | None:
    """IS-02 (auditoría de informes simples, sesión 2026-08-01) — el filtro
    por actor ya existía en el backend (`usuario_id`) pero no había ningún
    control en la UI para usarlo (un director no conoce el id interno de un
    usuario). Se filtra por email, que sí es un dato que el director tiene a
    mano, y se resuelve a `usuario_id` acá. Si el email no existe, se
    devuelve un id imposible para que el filtro no se ignore en silencio y
    en cambio muestre "sin resultados"."""
    if not actor_email:
        return None
    usuario = await SeguridadRepository().get_usuario_by_email(actor_email)
    return usuario["id"] if usuario else "__sin_coincidencia__"


@router.get("")
async def listar(
    request: Request,
    actor_email: str | None = None,
    accion: str | None = None,
    tabla: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("seguridad", "ver", "auditoria")),
):
    repo = SeguridadRepository()
    usuario_id = await _resolver_actor_id(actor_email)
    filtro = _construir_filtro(usuario_id, accion, tabla, desde, hasta)
    resultado = await repo.list_auditoria(filtro=filtro, page=page, per_page=25)
    pagina = Pagina(
        items=resultado["items"], pagina=resultado["page"], total_paginas=max(1, resultado["totalPages"]),
        total_items=resultado["totalItems"], tamano_pagina=resultado["perPage"],
    )
    contexto = await nav_context(usuario)
    contexto.update({
        "pagina": pagina,
        "filtros": {
            "actor_email": actor_email or "",
            "accion": accion or "",
            "tabla": tabla or "",
            "desde": desde or "",
            "hasta": hasta or "",
        },
    })
    return templates.TemplateResponse(request, "admin/auditoria.html", contexto)


@router.get("/exportar")
async def exportar(
    actor_email: str | None = None,
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
    usuario_id = await _resolver_actor_id(actor_email)
    filtro = _construir_filtro(usuario_id, accion, tabla, desde, hasta)
    resultado = await repo.list_auditoria(filtro=filtro, per_page=500)
    return csv_response(
        resultado["items"],
        [
            ("fecha", lambda r: r["created"]),
            ("usuario_id", lambda r: r.get("usuario_id", "")),
            ("accion", lambda r: r["accion"]),
            ("tabla", lambda r: r["tabla"]),
            ("registro_id", lambda r: r.get("registro_id", "")),
            ("ip", lambda r: r.get("ip", "")),
            ("detalle", lambda r: r.get("detalle", "")),
        ],
        "auditoria.csv",
    )
