"""CU-T30 (cupones + T44 acumulación con paquete), CU-T31 (campañas de
email), CU-T32 (reporte de cupones) — Actor: Administrador únicamente,
sin rol Agente en este módulo (a diferencia de Centro de Ayuda)."""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.ofertas.integrations.campana_sender import CredencialNoConfigurada, SendGridCampanaSender
from app.ofertas.repositories.ofertas_repo import OfertasRepository
from app.ofertas.services.ofertas_service import (
    CampanaBloqueada,
    CuponInmutable,
    CuponInvalido,
    OfertaInvalida,
    SuscripcionInvalida,
    actualizar_cupon,
    actualizar_default_acumulacion,
    actualizar_oferta_destacada,
    alternar_activa_oferta,
    alternar_activo_cupon,
    alternar_activo_suscripcion,
    crear_campana,
    crear_cupon,
    crear_oferta_destacada,
    enviar_campana,
    reporte_cupones,
)
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.csv_export import csv_response
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/ofertas")


async def _rbac_ver(usuario: dict = Depends(requiere_permiso("ofertas", "ver"))):
    return usuario


async def _rbac_crear(usuario: dict = Depends(requiere_permiso("ofertas", "crear"))):
    return usuario


async def _rbac_editar(usuario: dict = Depends(requiere_permiso("ofertas", "editar"))):
    return usuario


@router.get("/cupones")
async def listar_cupones(
    request: Request,
    codigo: str = Query(""),
    tipo_cupon: str = Query(""),
    estado: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(_rbac_ver),
):
    cupones = await OfertasRepository().listar_cupones(
        codigo=codigo or None, tipo=tipo_cupon or None, estado=estado or None
    )
    pagina = paginar(cupones, page)
    contexto = await nav_context(usuario)
    contexto.update({"pagina": pagina, "filtros": {"codigo": codigo, "tipo_cupon": tipo_cupon, "estado": estado}})
    return templates.TemplateResponse(request, "backoffice/cupones.html", contexto)


@router.post("/cupones")
async def crear_cupon_endpoint(
    codigo: str = Form(...), tipo: str = Form(...), valor: float = Form(...),
    producto_aplicable: str = Form(""), fecha_expiracion: str = Form(...),
    usos_maximos: str = Form(""), acumulable_con_paquete: str = Form(""),
    usuario: dict = Depends(_rbac_crear),
):
    data = {
        "codigo": codigo, "tipo": tipo, "valor": valor, "fecha_expiracion": fecha_expiracion,
        "producto_aplicable": producto_aplicable or None,
        "usos_maximos": int(usos_maximos) if usos_maximos.strip() else None,
    }
    if acumulable_con_paquete in ("true", "false"):
        data["acumulable_con_paquete"] = acumulable_con_paquete == "true"
    await crear_cupon(usuario, data)
    return redirect_con_mensaje("/backoffice/ofertas/cupones", "Cupón creado")


@router.post("/cupones/{cupon_id}")
async def editar_cupon_endpoint(
    cupon_id: str,
    tipo: str = Form(...), valor: float = Form(...), producto_aplicable: str = Form(""),
    fecha_expiracion: str = Form(...), usos_maximos: str = Form(""),
    acumulable_con_paquete: str = Form(""),
    usuario: dict = Depends(_rbac_editar),
):
    data = {
        "tipo": tipo, "valor": valor, "fecha_expiracion": fecha_expiracion,
        "producto_aplicable": producto_aplicable or None,
        "usos_maximos": int(usos_maximos) if usos_maximos.strip() else None,
    }
    if acumulable_con_paquete in ("true", "false"):
        data["acumulable_con_paquete"] = acumulable_con_paquete == "true"
    else:
        data["acumulable_con_paquete"] = None
    try:
        await actualizar_cupon(usuario, cupon_id, data)
    except (CuponInvalido, CuponInmutable) as exc:
        return redirect_con_mensaje("/backoffice/ofertas/cupones", str(exc), tipo="error")
    return redirect_con_mensaje("/backoffice/ofertas/cupones", "Cupón actualizado")


@router.post("/cupones/{cupon_id}/alternar-activo")
async def alternar_activo_cupon_endpoint(cupon_id: str, usuario: dict = Depends(_rbac_editar)):
    try:
        actualizado = await alternar_activo_cupon(usuario, cupon_id)
    except CuponInvalido as exc:
        return redirect_con_mensaje("/backoffice/ofertas/cupones", str(exc), tipo="error")
    mensaje = "Cupón reactivado" if actualizado["activo"] else "Cupón desactivado"
    return redirect_con_mensaje("/backoffice/ofertas/cupones", mensaje)


@router.get("/suscriptores")
async def listar_suscriptores(
    request: Request,
    email: str = Query(""),
    estado: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(_rbac_ver),
):
    suscriptores = await OfertasRepository().listar_todos_suscriptores(
        email=email or None, estado=estado or None
    )
    pagina = paginar(suscriptores, page)
    contexto = await nav_context(usuario)
    contexto.update({"pagina": pagina, "filtros": {"email": email, "estado": estado}})
    return templates.TemplateResponse(request, "backoffice/suscriptores.html", contexto)


@router.post("/suscriptores/{suscripcion_id}/alternar-activo")
async def alternar_activo_suscripcion_endpoint(suscripcion_id: str, usuario: dict = Depends(_rbac_editar)):
    try:
        actualizado = await alternar_activo_suscripcion(usuario, suscripcion_id)
    except SuscripcionInvalida as exc:
        return redirect_con_mensaje("/backoffice/ofertas/suscriptores", str(exc), tipo="error")
    mensaje = "Suscripción reactivada" if actualizado["activo"] else "Suscripción desactivada"
    return redirect_con_mensaje("/backoffice/ofertas/suscriptores", mensaje)


@router.get("/reporte-cupones")
async def reporte_cupones_endpoint(request: Request, dias: int = 90, usuario: dict = Depends(_rbac_ver)):
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S.000Z")
    reporte_data = await reporte_cupones(desde)
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(
        request, "backoffice/reporte_cupones.html", {**contexto, "reporte": reporte_data, "dias": dias}
    )


async def _favoritos_filtrados(tipo: str, desde: str, hasta: str) -> tuple[list[dict], list[str], int]:
    favoritos = await CuentaRepository().listar_todos_favoritos()
    tipos_disponibles = sorted({f.get("tipo") or "sin_tipo" for f in favoritos})

    if tipo:
        favoritos = [f for f in favoritos if (f.get("tipo") or "sin_tipo") == tipo]
    if desde:
        favoritos = [f for f in favoritos if (f.get("fecha_guardado") or "") >= desde]
    if hasta:
        favoritos = [f for f in favoritos if (f.get("fecha_guardado") or "") <= hasta]

    conteo: dict[tuple[str, str], int] = {}
    for f in favoritos:
        clave = (f.get("tipo") or "sin_tipo", f.get("producto_ref") or "—")
        conteo[clave] = conteo.get(clave, 0) + 1

    ranking = sorted(
        ({"tipo": t, "producto_ref": ref, "veces_guardado": cantidad} for (t, ref), cantidad in conteo.items()),
        key=lambda r: r["veces_guardado"],
        reverse=True,
    )
    return ranking, tipos_disponibles, len(favoritos)


@router.get("/reporte-favoritos")
async def reporte_favoritos_endpoint(
    request: Request,
    tipo: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(_rbac_ver),
):
    """CU-T55 — destinos/productos más guardados por los pasajeros. IS-23
    (auditoría de informes simples, sesión 2026-08-01) — filtro por tipo y
    período (sobre `fecha_guardado`), y paginación del ranking; el orden
    descendente por conteo ya existía."""
    ranking, tipos_disponibles, total_favoritos = await _favoritos_filtrados(tipo, desde, hasta)
    pagina = paginar(ranking, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "total_favoritos": total_favoritos,
            "tipos": tipos_disponibles,
            "filtros": {"tipo": tipo, "desde": desde, "hasta": hasta},
        }
    )
    return templates.TemplateResponse(request, "backoffice/reporte_favoritos.html", contexto)


@router.get("/reporte-favoritos/exportar")
async def exportar_favoritos(
    tipo: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    usuario: dict = Depends(_rbac_ver),
):
    ranking, _tipos, _total = await _favoritos_filtrados(tipo, desde, hasta)
    return csv_response(
        ranking,
        [
            ("tipo", lambda r: r["tipo"]),
            ("producto", lambda r: r["producto_ref"]),
            ("veces_guardado", lambda r: r["veces_guardado"]),
        ],
        "favoritos_ranking.csv",
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
async def listar_campanas(request: Request, page: int = Query(1, ge=1), usuario: dict = Depends(_rbac_ver)):
    campanas = await OfertasRepository().listar_campanas()
    pagina = paginar(campanas, page)
    contexto = await nav_context(usuario)
    contexto.update({"pagina": pagina})
    return templates.TemplateResponse(request, "backoffice/campanas.html", contexto)


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
    return redirect_con_mensaje("/backoffice/ofertas/campanas", "Campaña creada como borrador")


@router.post("/campanas/{campana_id}/enviar")
async def enviar_campana_endpoint(campana_id: str, usuario: dict = Depends(_rbac_editar)):
    try:
        await enviar_campana(usuario, campana_id, SendGridCampanaSender())
    except CredencialNoConfigurada:
        return redirect_con_mensaje(
            "/backoffice/ofertas/campanas",
            "No hay credencial real de SendGrid configurada — el envío no se simula",
            tipo="error",
        )
    except CampanaBloqueada as exc:
        return redirect_con_mensaje("/backoffice/ofertas/campanas", str(exc), tipo="error")
    return redirect_con_mensaje("/backoffice/ofertas/campanas", "Campaña enviada")


# ── WP-17 (auditoría de WorkPanels, 2026-08-01) — ofertas destacadas,
# antes sin ningún panel de gestión (solo se leían para el home público) ──

@router.get("/destacadas")
async def listar_ofertas_destacadas(
    request: Request,
    tipo_producto: str = Query(""),
    estado: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(_rbac_ver),
):
    ofertas = await OfertasRepository().listar_ofertas_admin(tipo_producto=tipo_producto or None, estado=estado or None)
    pagina = paginar(ofertas, page)
    contexto = await nav_context(usuario)
    contexto.update({"pagina": pagina, "filtros": {"tipo_producto": tipo_producto, "estado": estado}})
    return templates.TemplateResponse(request, "backoffice/ofertas_destacadas.html", contexto)


@router.post("/destacadas")
async def crear_oferta_destacada_endpoint(
    tipo_producto: str = Form(...), producto_ref: str = Form(...), titulo: str = Form(...),
    descripcion: str = Form(""), fecha_inicio: str = Form(...), fecha_fin: str = Form(...),
    usuario: dict = Depends(_rbac_crear),
):
    data = {
        "tipo_producto": tipo_producto, "producto_ref": producto_ref, "titulo": titulo,
        "descripcion": descripcion or None, "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
        "activa": True,
    }
    await crear_oferta_destacada(usuario, data)
    return redirect_con_mensaje("/backoffice/ofertas/destacadas", "Oferta creada")


@router.post("/destacadas/{oferta_id}")
async def editar_oferta_destacada_endpoint(
    oferta_id: str,
    tipo_producto: str = Form(...), producto_ref: str = Form(...), titulo: str = Form(...),
    descripcion: str = Form(""), fecha_inicio: str = Form(...), fecha_fin: str = Form(...),
    usuario: dict = Depends(_rbac_editar),
):
    data = {
        "tipo_producto": tipo_producto, "producto_ref": producto_ref, "titulo": titulo,
        "descripcion": descripcion or None, "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
    }
    try:
        await actualizar_oferta_destacada(usuario, oferta_id, data)
    except OfertaInvalida as exc:
        return redirect_con_mensaje("/backoffice/ofertas/destacadas", str(exc), tipo="error")
    return redirect_con_mensaje("/backoffice/ofertas/destacadas", "Oferta actualizada")


@router.post("/destacadas/{oferta_id}/alternar-activa")
async def alternar_activa_oferta_endpoint(oferta_id: str, usuario: dict = Depends(_rbac_editar)):
    try:
        actualizada = await alternar_activa_oferta(usuario, oferta_id)
    except OfertaInvalida as exc:
        return redirect_con_mensaje("/backoffice/ofertas/destacadas", str(exc), tipo="error")
    mensaje = "Oferta reactivada" if actualizada["activa"] else "Oferta desactivada"
    return redirect_con_mensaje("/backoffice/ofertas/destacadas", mensaje)
