"""CU-T28 (gestionar artículos, Administrador), CU-T29 (métricas de
satisfacción, Administrador), CU-T36 (bandeja de casos escalados,
Agente) — RBAC de dos niveles: Nivel 1 (módulo `centro_ayuda`) autoriza a
ambos roles; Nivel 2 (`roles_permisos_tablas`) restringe a Agente a la
tabla `casos_escalados` (sembrado en `scripts/seed_centro_ayuda_rbac.py`)
para que solo Administrador pueda gestionar artículos/métricas."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.centro_ayuda.services.centro_ayuda_service import (
    actualizar_articulo,
    crear_articulo,
    metricas_satisfaccion,
    resolver_caso,
)
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/ayuda")


async def _rbac_ver_articulos(usuario: dict = Depends(requiere_permiso("centro_ayuda", "ver", "articulos_ayuda"))):
    return usuario


async def _rbac_gestionar_articulos(
    usuario: dict = Depends(requiere_permiso("centro_ayuda", "crear", "articulos_ayuda")),
):
    return usuario


async def _rbac_ver_casos(usuario: dict = Depends(requiere_permiso("centro_ayuda", "ver", "casos_escalados"))):
    return usuario


async def _rbac_resolver_casos(usuario: dict = Depends(requiere_permiso("centro_ayuda", "editar", "casos_escalados"))):
    return usuario


@router.get("/articulos")
async def listar_articulos(request: Request, usuario: dict = Depends(_rbac_ver_articulos)):
    articulos = await CentroAyudaRepository().listar_articulos_admin()
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(request, "backoffice/articulos.html", {**contexto, "articulos": articulos})


@router.post("/articulos")
async def crear(
    categoria: str = Form(...), titulo: str = Form(...), contenido: str = Form(...),
    usuario: dict = Depends(_rbac_gestionar_articulos),
):
    await crear_articulo(usuario, categoria, titulo, contenido)
    return RedirectResponse("/backoffice/ayuda/articulos?mensaje=Artículo creado", status_code=303)


@router.post("/articulos/{articulo_id}")
async def editar(
    articulo_id: str,
    categoria: str = Form(...), titulo: str = Form(...), contenido: str = Form(...),
    activo: bool = Form(False),
    usuario: dict = Depends(_rbac_gestionar_articulos),
):
    await actualizar_articulo(usuario, articulo_id, categoria, titulo, contenido, activo)
    return RedirectResponse("/backoffice/ayuda/articulos?mensaje=Artículo actualizado", status_code=303)


@router.get("/metricas")
async def metricas(request: Request, dias: int = 90, usuario: dict = Depends(_rbac_ver_articulos)):
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S.000Z")
    resumen = await metricas_satisfaccion(desde)
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(
        request, "backoffice/metricas.html", {**contexto, "resumen": resumen, "dias": dias}
    )


@router.get("/casos")
async def listar_casos(request: Request, estado: str | None = None, usuario: dict = Depends(_rbac_ver_casos)):
    repo = CentroAyudaRepository()
    casos = await repo.listar_casos(estado)
    pasajeros_repo = PasajerosRepository()
    casos_out = []
    for c in casos:
        pasajero = await pasajeros_repo.obtener_pasajero(c["pasajero_id"])
        nombre = None
        if pasajero:
            usuario_pasajero = await pasajeros_repo.usuario_por_id(pasajero["usuario_id"])
            nombre = usuario_pasajero["nombre_completo"] if usuario_pasajero else None
        casos_out.append({**c, "pasajero_nombre": nombre})
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(
        request, "backoffice/casos.html", {**contexto, "casos": casos_out, "estado_filtro": estado or ""}
    )


@router.post("/casos/{caso_id}/resolver")
async def resolver(caso_id: str, usuario: dict = Depends(_rbac_resolver_casos)):
    await resolver_caso(caso_id, usuario["id"])
    return RedirectResponse("/backoffice/ayuda/casos?mensaje=Caso marcado como resuelto", status_code=303)
