"""Fase B.4 (docs/estrategico-auditoria.md) — KPI manual de CAC digital
(OE-1, Balanced Scorecard). Sin fuente real de costo de canal/campaña en
el sistema (bloqueante documentado en la auditoría), así que el admin lo
ingresa a mano; el dashboard DS-00 (Fase C, todavía no implementado) lo
consume desde acá y lo muestra con badge "Ingresado manualmente".

Módulo RBAC dedicado `estrategico` (no `dashboards` ni `configuracion`) —
ver `scripts/seed_estrategico_rbac.py`: "admin_general" de la spec no
existe como rol literal en el sistema real, el rol equivalente es
`Administrador` (mismo criterio que ya usa `dashboards` para ese rol)."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse

from app.dashboards.services.estrategico_service import (
    obtener_datos_cockpit,
    obtener_datos_disrupciones_global,
    obtener_datos_inteligencia,
    obtener_datos_oferta,
)
from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/estrategico")

CLAVE_VALOR = "cac_digital_actual"
CLAVE_PERIODO = "cac_digital_periodo"


def _parse_fecha(valor: str | None, default: datetime.date) -> datetime.date:
    if not valor:
        return default
    try:
        return datetime.date.fromisoformat(valor)
    except ValueError:
        return default


def _registrar_dashboard_estrategico(ruta: str, clave: str, template: str, obtener_datos) -> None:
    """Wiring genérico para DS-00 a DS-03 — mismo patrón que
    `router_backoffice.py::_registrar_dashboard`, pero sin Nivel 2 por
    tabla (el módulo `estrategico` es todo o nada, ver seed_estrategico_rbac.py)."""

    @router.get(f"/{ruta}", name=f"dashboard_estrategico_{clave}")
    async def _pagina(request: Request, usuario: dict = Depends(requiere_permiso("estrategico", "ver"))):
        contexto = await nav_context(usuario)
        return templates.TemplateResponse(request, f"backoffice/{template}", contexto)

    @router.get(f"/{ruta}/datos", name=f"dashboard_estrategico_{clave}_datos")
    async def _datos(
        desde: str | None = None,
        hasta: str | None = None,
        usuario: dict = Depends(requiere_permiso("estrategico", "ver")),
    ):
        hoy = datetime.date.today()
        fecha_desde = _parse_fecha(desde, hoy.replace(day=1))
        fecha_hasta = _parse_fecha(hasta, hoy)
        datos = await obtener_datos(fecha_desde, fecha_hasta)
        return JSONResponse(datos)


_registrar_dashboard_estrategico("cockpit", "cockpit", "estrategico_cockpit.html", obtener_datos_cockpit)
_registrar_dashboard_estrategico("oferta", "oferta", "estrategico_oferta.html", obtener_datos_oferta)
_registrar_dashboard_estrategico("disrupciones", "disrupciones", "estrategico_disrupciones.html", obtener_datos_disrupciones_global)
_registrar_dashboard_estrategico("inteligencia", "inteligencia", "estrategico_inteligencia.html", obtener_datos_inteligencia)


@router.get("/config/cac")
async def obtener_cac(usuario: dict = Depends(requiere_permiso("estrategico", "ver"))):
    repo = SeguridadRepository()
    valor = await repo.get_config(CLAVE_VALOR)
    periodo = await repo.get_config(CLAVE_PERIODO)
    return JSONResponse({
        "valor": float(valor["valor"]) if valor else 0.0,
        "periodo": periodo["valor"] if periodo and periodo["valor"] != "—" else None,
        "ingresado_manualmente": True,
    })


@router.post("/config/cac")
async def actualizar_cac(
    valor: float = Form(...),
    periodo: str = Form(...),
    usuario: dict = Depends(requiere_permiso("estrategico", "editar")),
):
    repo = SeguridadRepository()
    await repo.actualizar_config(CLAVE_VALOR, str(valor), usuario["id"])
    await repo.actualizar_config(CLAVE_PERIODO, periodo, usuario["id"])
    await AuditService().insertar(
        "editar", "configuracion_sistema", usuario_id=usuario["id"],
        detalle={"clave": CLAVE_VALOR, "valor": valor, "periodo": periodo},
    )
    return JSONResponse({"valor": valor, "periodo": periodo, "ingresado_manualmente": True})
