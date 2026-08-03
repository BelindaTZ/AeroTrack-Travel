"""CU-T28 (gestionar artículos, Administrador), CU-T29 (métricas de
satisfacción, Administrador), CU-T36 (bandeja de casos escalados,
Agente) — RBAC de dos niveles: Nivel 1 (módulo `centro_ayuda`) autoriza a
ambos roles; Nivel 2 (`roles_permisos_tablas`) restringe a Agente a la
tabla `casos_escalados` (sembrado en `scripts/seed_centro_ayuda_rbac.py`)
para que solo Administrador pueda gestionar artículos/métricas.

WP-05 (auditoría de WorkPanels, 2026-07-31) — filtros (categoría, estado,
texto), paginación, y modal de Crear/Editar/Ver/Archivar en vez del
acordeón de antes.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Query, Request

from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.centro_ayuda.services.centro_ayuda_service import (
    ArticuloNoEncontrado,
    actualizar_articulo,
    archivar_articulo,
    crear_articulo,
    metricas_satisfaccion,
    resolver_caso,
)
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.csv_export import csv_response
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
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
async def listar_articulos(
    request: Request,
    categoria: str = Query(""),
    estado: str = Query(""),
    texto: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(_rbac_ver_articulos),
):
    repo = CentroAyudaRepository()
    articulos = await repo.listar_articulos_admin_filtrado(
        categoria=categoria or None, estado=estado or None, texto=texto or None
    )
    categorias = await repo.categorias_disponibles()
    pagina = paginar(articulos, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "categorias": categorias,
            "filtros": {"categoria": categoria, "estado": estado, "texto": texto},
        }
    )
    return templates.TemplateResponse(request, "backoffice/articulos.html", contexto)


@router.post("/articulos")
async def crear(
    categoria: str = Form(...), titulo: str = Form(...), contenido: str = Form(...),
    usuario: dict = Depends(_rbac_gestionar_articulos),
):
    await crear_articulo(usuario, categoria, titulo, contenido)
    return redirect_con_mensaje("/backoffice/ayuda/articulos", "Artículo creado")


@router.post("/articulos/{articulo_id}")
async def editar(
    articulo_id: str,
    categoria: str = Form(...), titulo: str = Form(...), contenido: str = Form(...),
    usuario: dict = Depends(_rbac_gestionar_articulos),
):
    repo = CentroAyudaRepository()
    actual = await repo.obtener_articulo(articulo_id)
    if actual is None:
        return redirect_con_mensaje("/backoffice/ayuda/articulos", "Artículo no encontrado", tipo="error")
    # El estado activo/archivado se cambia solo desde "Archivar"/"Reactivar"
    # (acción propia, con su propia confirmación) — Editar nunca lo toca.
    await actualizar_articulo(usuario, articulo_id, categoria, titulo, contenido, actual.get("activo", True))
    return redirect_con_mensaje("/backoffice/ayuda/articulos", "Artículo actualizado")


@router.post("/articulos/{articulo_id}/archivar")
async def archivar(
    articulo_id: str,
    usuario: dict = Depends(_rbac_gestionar_articulos),
):
    try:
        actualizado = await archivar_articulo(usuario, articulo_id)
    except ArticuloNoEncontrado:
        return redirect_con_mensaje("/backoffice/ayuda/articulos", "Artículo no encontrado", tipo="error")

    mensaje = "Artículo reactivado" if actualizado["activo"] else "Artículo archivado"
    return redirect_con_mensaje("/backoffice/ayuda/articulos", mensaje)


@router.get("/metricas")
async def metricas(request: Request, dias: int = 90, usuario: dict = Depends(_rbac_ver_articulos)):
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S.000Z")
    resumen = await metricas_satisfaccion(desde)
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(
        request, "backoffice/metricas.html", {**contexto, "resumen": resumen, "dias": dias}
    )


def _dias_abierto(caso: dict) -> int | None:
    """IS-13 (auditoría de informes simples, sesión 2026-08-01) — antes la
    "antigüedad" solo se podía leer indirectamente por el orden de la lista
    (más nuevo primero); acá se calcula un valor explícito en días, contra
    `fecha_resolucion` si ya está resuelto o contra "ahora" si sigue abierto."""
    if not caso.get("fecha_creacion"):
        return None
    try:
        creado = datetime.fromisoformat(caso["fecha_creacion"].replace("Z", "+00:00"))
    except ValueError:
        return None
    if caso.get("fecha_resolucion"):
        try:
            hasta = datetime.fromisoformat(caso["fecha_resolucion"].replace("Z", "+00:00"))
        except ValueError:
            hasta = datetime.now(timezone.utc)
    else:
        hasta = datetime.now(timezone.utc)
    return (hasta - creado).days


async def _casos_filtrados(
    estado: str | None, mi_bandeja: bool, desde: str | None, hasta: str | None, usuario: dict
) -> list[dict]:
    repo = CentroAyudaRepository()
    casos = await repo.listar_casos(estado, desde=desde or None, hasta=hasta or None)
    if mi_bandeja:
        # CU-T36/T46 — "mi bandeja activa" de un Agente: casos todavía
        # abiertos (pool disponible para tomar, no hay asignación previa a
        # la resolución) más los que YO ya resolví — ver
        # `resolver_caso()`, que recién ahí escribe `agente_asignado_id`.
        casos = [
            c for c in casos
            if c.get("estado") == "abierto" or c.get("agente_asignado_id") == usuario["id"]
        ]
    pasajeros_repo = PasajerosRepository()
    casos_out = []
    for c in casos:
        pasajero = await pasajeros_repo.obtener_pasajero(c["pasajero_id"])
        nombre = email = telefono = None
        if pasajero:
            telefono = pasajero.get("telefono")
            usuario_pasajero = await pasajeros_repo.usuario_por_id(pasajero["usuario_id"])
            if usuario_pasajero:
                nombre = usuario_pasajero["nombre_completo"]
                email = usuario_pasajero.get("email")
        agente_nombre = None
        if c.get("agente_asignado_id"):
            agente = await pasajeros_repo.usuario_por_id(c["agente_asignado_id"])
            agente_nombre = agente["nombre_completo"] if agente else None
        casos_out.append(
            {**c, "pasajero_nombre": nombre, "pasajero_email": email, "pasajero_telefono": telefono,
             "agente_nombre": agente_nombre, "dias_abierto": _dias_abierto(c)}
        )
    return casos_out


@router.get("/casos")
async def listar_casos(
    request: Request,
    estado: str | None = None,
    mi_bandeja: bool = False,
    desde: str = Query(""),
    hasta: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(_rbac_ver_casos),
):
    casos_out = await _casos_filtrados(estado, mi_bandeja, desde, hasta, usuario)
    pagina = paginar(casos_out, page)
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(
        request,
        "backoffice/casos.html",
        {
            **contexto, "pagina": pagina, "estado_filtro": estado or "", "mi_bandeja": mi_bandeja,
            "filtros": {"desde": desde, "hasta": hasta},
        },
    )


@router.get("/casos/exportar")
async def exportar_casos(
    estado: str | None = None,
    mi_bandeja: bool = False,
    desde: str = Query(""),
    hasta: str = Query(""),
    usuario: dict = Depends(_rbac_ver_casos),
):
    casos_out = await _casos_filtrados(estado, mi_bandeja, desde, hasta, usuario)
    return csv_response(
        casos_out,
        [
            ("fecha_creacion", lambda c: c.get("fecha_creacion", "")),
            ("asunto", lambda c: c["asunto"]),
            ("pasajero", lambda c: c.get("pasajero_nombre") or ""),
            ("estado", lambda c: c["estado"]),
            ("dias_abierto", lambda c: c["dias_abierto"] if c["dias_abierto"] is not None else ""),
            ("agente", lambda c: c.get("agente_nombre") or ""),
        ],
        "casos_escalados.csv",
    )


@router.post("/casos/{caso_id}/resolver")
async def resolver(caso_id: str, usuario: dict = Depends(_rbac_resolver_casos)):
    await resolver_caso(caso_id, usuario["id"])
    return redirect_con_mensaje("/backoffice/ayuda/casos", "Caso marcado como resuelto")
