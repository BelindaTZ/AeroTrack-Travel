"""DB-01 a DB-03 y DB-05 a DB-13 — dashboards del backoffice (DB-04 es
pasajero-facing, vive en `app/vuelos/router_busqueda.py`). Cada dashboard
usa `requiere_permiso("dashboards", "ver", tabla=<clave>)` — Nivel 2 sobre
el único módulo "dashboards" (ver `scripts/seed_dashboards_rbac.py` para
por qué está modelado así en vez de una acción custom por dashboard)."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.dashboards.services.agentes_service import obtener_datos_agentes
from app.dashboards.services.alertas_precio_service import obtener_datos_alertas_precio
from app.dashboards.services.asistente_ia_service import obtener_datos_asistente_ia
from app.dashboards.services.campanas_service import obtener_datos_campanas
from app.dashboards.services.catalogo_rutas_service import obtener_datos_catalogo_rutas
from app.dashboards.services.clientes_service import obtener_datos_clientes
from app.dashboards.services.comercial_service import obtener_datos_comercial
from app.dashboards.services.demanda_service import obtener_datos_demanda
from app.dashboards.services.disrupciones_service import obtener_datos_disrupciones
from app.dashboards.services.finanzas_service import obtener_datos_finanzas
from app.dashboards.services.paquetes_service import obtener_datos_paquetes
from app.dashboards.services.soporte_service import obtener_datos_soporte
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.pocketbase_client import get_pocketbase_client
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/dashboards")


def _parse_fecha(valor: str | None, default: datetime.date) -> datetime.date:
    if not valor:
        return default
    try:
        return datetime.date.fromisoformat(valor)
    except ValueError:
        return default


def _registrar_dashboard(ruta: str, tabla: str, template: str, obtener_datos) -> None:
    """Wiring genérico para los dashboards sin ninguna excepción especial
    (comercial tiene el caso 👁 de exportar, se define a mano arriba)."""

    @router.get(f"/{ruta}", name=f"dashboard_{tabla}")
    async def _pagina(request: Request, usuario: dict = Depends(requiere_permiso("dashboards", "ver", tabla=tabla))):
        contexto = await nav_context(usuario)
        return templates.TemplateResponse(request, f"backoffice/{template}", contexto)

    @router.get(f"/{ruta}/datos", name=f"dashboard_{tabla}_datos")
    async def _datos(
        desde: str | None = None,
        hasta: str | None = None,
        usuario: dict = Depends(requiere_permiso("dashboards", "ver", tabla=tabla)),
    ):
        hoy = datetime.date.today()
        fecha_desde = _parse_fecha(desde, hoy.replace(day=1))
        fecha_hasta = _parse_fecha(hasta, hoy)
        datos = await obtener_datos(fecha_desde, fecha_hasta)
        return JSONResponse(datos)


@router.get("/comercial")
async def comercial(request: Request, usuario: dict = Depends(requiere_permiso("dashboards", "ver", tabla="comercial"))):
    contexto = await nav_context(usuario)
    # 👁 spec DB-01: admin_finanzas tiene "ver" pero no "exportar" acá
    # puntualmente (sí exporta DB-02) — el schema de roles_permisos_tablas
    # no soporta Nivel 2 para "exportar" (ver seed_dashboards_rbac.py), así
    # que esta única excepción de toda la matriz se resuelve acá por nombre
    # de rol en vez de con una tabla de permisos.
    rol = await get_pocketbase_client().get_record("roles", usuario["rol_id"]) if usuario.get("rol_id") else {}
    contexto["puede_exportar"] = rol.get("nombre") != "admin_finanzas"
    return templates.TemplateResponse(request, "backoffice/comercial.html", contexto)


@router.get("/comercial/datos")
async def comercial_datos(
    desde: str | None = None,
    hasta: str | None = None,
    usuario: dict = Depends(requiere_permiso("dashboards", "ver", tabla="comercial")),
):
    hoy = datetime.date.today()
    fecha_desde = _parse_fecha(desde, hoy.replace(day=1))
    fecha_hasta = _parse_fecha(hasta, hoy)
    datos = await obtener_datos_comercial(fecha_desde, fecha_hasta)
    return JSONResponse(datos)


_registrar_dashboard("finanzas", "finanzas", "finanzas.html", obtener_datos_finanzas)
_registrar_dashboard("disrupciones", "operaciones", "disrupciones_dashboard.html", obtener_datos_disrupciones)
_registrar_dashboard("clientes", "clientes", "clientes.html", obtener_datos_clientes)
_registrar_dashboard("demanda", "demanda", "demanda.html", obtener_datos_demanda)
_registrar_dashboard("paquetes", "paquetes", "paquetes.html", obtener_datos_paquetes)
_registrar_dashboard("catalogo-rutas", "catalogo_rutas", "catalogo_rutas.html", obtener_datos_catalogo_rutas)
_registrar_dashboard("soporte", "soporte", "soporte.html", obtener_datos_soporte)
_registrar_dashboard("campanas", "campanas", "campanas_dashboard.html", obtener_datos_campanas)
_registrar_dashboard("asistente-ia", "asistente_ia", "asistente_ia.html", obtener_datos_asistente_ia)
_registrar_dashboard("alertas-precio", "alertas_precio", "alertas_precio.html", obtener_datos_alertas_precio)


@router.get("/agentes")
async def agentes(request: Request, usuario: dict = Depends(requiere_permiso("dashboards", "ver", tabla="agentes"))):
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(request, "backoffice/agentes.html", contexto)


@router.get("/agentes/datos")
async def agentes_datos(
    desde: str | None = None,
    hasta: str | None = None,
    usuario: dict = Depends(requiere_permiso("dashboards", "ver", tabla="agentes")),
):
    hoy = datetime.date.today()
    fecha_desde = _parse_fecha(desde, hoy.replace(day=1))
    fecha_hasta = _parse_fecha(hasta, hoy)
    # Vista propia si el rol es "Agente" (ve solo su cartera); vista global
    # para admin_operaciones/Administrador (ambos también tienen "ver" en
    # esta tabla, ver seed_dashboards_rbac.py).
    rol = await get_pocketbase_client().get_record("roles", usuario["rol_id"]) if usuario.get("rol_id") else {}
    agente_id = usuario["id"] if rol.get("nombre") == "Agente" else None
    datos = await obtener_datos_agentes(fecha_desde, fecha_hasta, agente_id=agente_id)
    return JSONResponse(datos)
