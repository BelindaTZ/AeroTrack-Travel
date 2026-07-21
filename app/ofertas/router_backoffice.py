"""CU-T30 (cupones + T44 acumulación con paquete), CU-T31 (campañas de
email), CU-T32 (reporte de cupones) — Actor: Administrador únicamente,
sin rol Agente en este módulo (a diferencia de Centro de Ayuda)."""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.ofertas.integrations.campana_sender import CredencialNoConfigurada, SendGridCampanaSender
from app.ofertas.repositories.ofertas_repo import OfertasRepository
from app.ofertas.services.ofertas_service import (
    CampanaBloqueada,
    CuponInmutable,
    CuponInvalido,
    actualizar_cupon,
    actualizar_default_acumulacion,
    crear_campana,
    crear_cupon,
    enviar_campana,
    reporte_cupones,
)
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/ofertas")


async def _rbac_ver(usuario: dict = Depends(requiere_permiso("ofertas", "ver"))):
    return usuario


async def _rbac_crear(usuario: dict = Depends(requiere_permiso("ofertas", "crear"))):
    return usuario


async def _rbac_editar(usuario: dict = Depends(requiere_permiso("ofertas", "editar"))):
    return usuario


@router.get("/cupones")
async def listar_cupones(request: Request, usuario: dict = Depends(_rbac_ver)):
    cupones = await OfertasRepository().listar_cupones()
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(request, "backoffice/cupones.html", {**contexto, "cupones": cupones})


@router.post("/cupones")
async def crear_cupon_endpoint(
    codigo: str = Form(...), tipo: str = Form(...), valor: float = Form(...),
    producto_aplicable: str = Form(""), fecha_expiracion: str = Form(...),
    usos_maximos: int | None = Form(None), acumulable_con_paquete: str = Form(""),
    usuario: dict = Depends(_rbac_crear),
):
    data = {
        "codigo": codigo, "tipo": tipo, "valor": valor, "fecha_expiracion": fecha_expiracion,
        "producto_aplicable": producto_aplicable or None, "usos_maximos": usos_maximos,
    }
    if acumulable_con_paquete in ("true", "false"):
        data["acumulable_con_paquete"] = acumulable_con_paquete == "true"
    await crear_cupon(usuario, data)
    return RedirectResponse("/backoffice/ofertas/cupones?mensaje=Cupón creado", status_code=303)


@router.post("/cupones/{cupon_id}")
async def editar_cupon_endpoint(
    cupon_id: str,
    tipo: str = Form(...), valor: float = Form(...), producto_aplicable: str = Form(""),
    fecha_expiracion: str = Form(...), usos_maximos: int | None = Form(None),
    acumulable_con_paquete: str = Form(""), activo: bool = Form(False),
    usuario: dict = Depends(_rbac_editar),
):
    data = {
        "tipo": tipo, "valor": valor, "fecha_expiracion": fecha_expiracion, "activo": activo,
        "producto_aplicable": producto_aplicable or None, "usos_maximos": usos_maximos,
    }
    if acumulable_con_paquete in ("true", "false"):
        data["acumulable_con_paquete"] = acumulable_con_paquete == "true"
    else:
        data["acumulable_con_paquete"] = None
    try:
        await actualizar_cupon(usuario, cupon_id, data)
    except (CuponInvalido, CuponInmutable) as exc:
        return RedirectResponse(f"/backoffice/ofertas/cupones?mensaje={exc}", status_code=303)
    return RedirectResponse("/backoffice/ofertas/cupones?mensaje=Cupón actualizado", status_code=303)


@router.get("/reporte-cupones")
async def reporte_cupones_endpoint(request: Request, dias: int = 90, usuario: dict = Depends(_rbac_ver)):
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S.000Z")
    reporte_data = await reporte_cupones(desde)
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(
        request, "backoffice/reporte_cupones.html", {**contexto, "reporte": reporte_data, "dias": dias}
    )


@router.get("/config-acumulacion-paquete")
async def ver_config_acumulacion(request: Request, usuario: dict = Depends(_rbac_ver)):
    registro = await OfertasRepository().config("cupones.acumulable_con_paquete_default")
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(
        request, "backoffice/config_acumulacion.html",
        {**contexto, "acumulable_default": (registro or {}).get("valor") == "true"},
    )


@router.post("/config-acumulacion-paquete")
async def actualizar_config_acumulacion(acumulable: bool = Form(False), usuario: dict = Depends(_rbac_editar)):
    await actualizar_default_acumulacion(usuario, acumulable)
    return RedirectResponse("/backoffice/ofertas/config-acumulacion-paquete?mensaje=Configuración guardada", status_code=303)


@router.get("/campanas")
async def listar_campanas(request: Request, usuario: dict = Depends(_rbac_ver)):
    campanas = await OfertasRepository().listar_campanas()
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(request, "backoffice/campanas.html", {**contexto, "campanas": campanas})


@router.post("/campanas")
async def crear_campana_endpoint(
    nombre: str = Form(...), segmento_criterio: str = Form("{}"), plantilla: str = Form(...),
    usuario: dict = Depends(_rbac_crear),
):
    try:
        criterio = json.loads(segmento_criterio) if segmento_criterio.strip() else {}
    except ValueError:
        criterio = {}
    await crear_campana(usuario, nombre, criterio, plantilla)
    return RedirectResponse("/backoffice/ofertas/campanas?mensaje=Campaña creada como borrador", status_code=303)


@router.post("/campanas/{campana_id}/enviar")
async def enviar_campana_endpoint(campana_id: str, usuario: dict = Depends(_rbac_editar)):
    try:
        await enviar_campana(usuario, campana_id, SendGridCampanaSender())
    except CredencialNoConfigurada:
        return RedirectResponse(
            "/backoffice/ofertas/campanas?mensaje=No hay credencial real de SendGrid configurada — el envío no se simula",
            status_code=303,
        )
    except CampanaBloqueada as exc:
        return RedirectResponse(f"/backoffice/ofertas/campanas?mensaje={exc}", status_code=303)
    return RedirectResponse("/backoffice/ofertas/campanas?mensaje=Campaña enviada", status_code=303)
