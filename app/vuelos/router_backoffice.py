"""RF-VUE-006 (CU-O48) — ajuste puntual excepcional, solo para demo.

Incluye obligatoriamente verificación de sesión (CU-O42), RBAC (CU-O43) y
auditoría (CU-O41) — primer consumidor real, fuera de Seguridad, de los 3
servicios transversales.
"""

import json

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.aerolineas_service import (
    AerolineaInvalida,
    actualizar_aerolinea,
    alternar_activa_aerolinea,
    crear_aerolinea,
)
from app.vuelos.services.asientos_service import (
    DEFAULT_HORAS_CHECKIN_GRATIS,
    DEFAULT_PCT_FILAS_PREMIUM,
    DEFAULT_RECARGO_PREMIUM,
)
from app.vuelos.services.enriquecimiento_service import (
    CLASES_CABINA,
    RUTAS_POR_CORRIDA_DEFAULT,
)
from app.vuelos.services.estado_service import ESTADOS_VALIDOS, EstadoInvalido
from app.vuelos.services.forzar_estado_service import MotivoRequerido, es_disrupcion, forzar_estado
from app.vuelos.services.tarifa_manual_service import (
    MotivoRequerido as MotivoTarifaRequerido,
)
from app.vuelos.services.tarifa_manual_service import TarifaInvalida, ajustar_tarifa_manual

router = APIRouter(prefix="/backoffice/vuelos")

_PERMISO_CONFIG = requiere_permiso("vuelos_catalogo", "editar", "vuelos_catalogo")


@router.get("")
async def listar_catalogo(
    request: Request,
    aerolinea_id: str = Query(""),
    origen: str = Query(""),
    destino: str = Query(""),
    fecha: str = Query(""),
    estado: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "ver", "vuelos_catalogo")),
):
    repo = VuelosRepository()
    vuelos = await repo.listar_vuelos_filtrado(
        aerolinea_id=aerolinea_id or None, origen=origen or None, destino=destino or None,
        fecha=fecha or None, estado=estado or None,
    )
    aerolineas = await repo.listar_aerolineas_activas()
    nombre_por_id = {a["id"]: a["nombre"] for a in aerolineas}
    vuelos_out = []
    for v in vuelos:
        tarifas = await repo.tarifas_de_vuelo(v["id"])
        vuelos_out.append({**v, "aerolinea_nombre": nombre_por_id.get(v["aerolinea_id"], "—"), "tarifas": tarifas})
    pagina = paginar(vuelos_out, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina, "aerolineas": aerolineas, "estados": sorted(ESTADOS_VALIDOS),
            "filtros": {"aerolinea_id": aerolinea_id, "origen": origen, "destino": destino, "fecha": fecha, "estado": estado},
        }
    )
    return templates.TemplateResponse(request, "backoffice/catalogo_vuelos.html", contexto)


@router.post("/tarifas/{tarifa_id}/ajustar")
async def ajustar_tarifa(
    tarifa_id: str,
    precio_final: float = Form(...),
    cupos_disponibles: str = Form(""),
    motivo: str = Form(...),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "editar", "tarifas_vuelo")),
):
    try:
        await ajustar_tarifa_manual(
            usuario, tarifa_id, precio_final,
            int(cupos_disponibles) if cupos_disponibles.strip() else None, motivo,
        )
    except MotivoTarifaRequerido:
        return redirect_con_mensaje("/backoffice/vuelos", "El motivo es obligatorio para ajustar una tarifa", tipo="error")
    except TarifaInvalida as exc:
        return redirect_con_mensaje("/backoffice/vuelos", str(exc), tipo="error")
    return redirect_con_mensaje("/backoffice/vuelos", "Tarifa ajustada")


@router.get("/aerolineas")
async def listar_aerolineas(
    request: Request,
    nombre: str = Query(""),
    estado: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "ver", "aerolineas")),
):
    repo = VuelosRepository()
    aerolineas = await repo.listar_aerolineas(nombre=nombre or None, estado=estado or None)
    pagina = paginar(aerolineas, page)
    contexto = await nav_context(usuario)
    contexto.update({"pagina": pagina, "filtros": {"nombre": nombre, "estado": estado}})
    return templates.TemplateResponse(request, "backoffice/aerolineas.html", contexto)


@router.post("/aerolineas")
async def crear_aerolinea_endpoint(
    nombre: str = Form(...),
    codigo_iata: str = Form(...),
    comision_pactada_pct: str = Form(""),
    contacto: str = Form(""),
    fecha_contrato: str = Form(""),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "crear", "aerolineas")),
):
    data = {
        "nombre": nombre, "codigo_iata": codigo_iata.upper(),
        "comision_pactada_pct": float(comision_pactada_pct) if comision_pactada_pct.strip() else None,
        "contacto": contacto or None, "fecha_contrato": fecha_contrato or None, "activa": True,
    }
    await crear_aerolinea(usuario, data)
    return redirect_con_mensaje("/backoffice/vuelos/aerolineas", "Aerolínea creada")


@router.post("/aerolineas/{aerolinea_id}")
async def editar_aerolinea_endpoint(
    aerolinea_id: str,
    nombre: str = Form(...),
    codigo_iata: str = Form(...),
    comision_pactada_pct: str = Form(""),
    contacto: str = Form(""),
    fecha_contrato: str = Form(""),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "editar", "aerolineas")),
):
    data = {
        "nombre": nombre, "codigo_iata": codigo_iata.upper(),
        "comision_pactada_pct": float(comision_pactada_pct) if comision_pactada_pct.strip() else None,
        "contacto": contacto or None, "fecha_contrato": fecha_contrato or None,
    }
    try:
        await actualizar_aerolinea(usuario, aerolinea_id, data)
    except AerolineaInvalida as exc:
        return redirect_con_mensaje("/backoffice/vuelos/aerolineas", str(exc), tipo="error")
    return redirect_con_mensaje("/backoffice/vuelos/aerolineas", "Aerolínea actualizada")


@router.post("/aerolineas/{aerolinea_id}/alternar-activa")
async def alternar_activa_aerolinea_endpoint(
    aerolinea_id: str,
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "editar", "aerolineas")),
):
    try:
        actualizada = await alternar_activa_aerolinea(usuario, aerolinea_id)
    except AerolineaInvalida as exc:
        return redirect_con_mensaje("/backoffice/vuelos/aerolineas", str(exc), tipo="error")
    mensaje = "Aerolínea reactivada" if actualizada["activa"] else "Aerolínea desactivada"
    return redirect_con_mensaje("/backoffice/vuelos/aerolineas", mensaje)


@router.get("/forzar-estado")
async def forzar_estado_form(
    request: Request,
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "editar", "vuelos_catalogo")),
):
    repo = VuelosRepository()
    vuelos = await repo.listar_para_selector()
    contexto = await nav_context(usuario)
    contexto.update({"vuelos_json": json.dumps(vuelos), "estados": sorted(ESTADOS_VALIDOS)})
    return templates.TemplateResponse(request, "backoffice/forzar_estado.html", contexto)


@router.post("/{vuelo_id}/forzar-estado")
async def forzar_estado_submit(
    vuelo_id: str,
    nuevo_estado: str = Form(...),
    motivo: str = Form(...),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "editar", "vuelos_catalogo")),
):
    try:
        actualizado = await forzar_estado(vuelo_id, nuevo_estado, motivo)
    except MotivoRequerido:
        return JSONResponse(
            status_code=400,
            content={"detail": "El motivo es obligatorio para forzar un ajuste (RN-VUE-006)"},
        )
    except EstadoInvalido as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    detalle = {"motivo": motivo, "origen": "demo"}
    if es_disrupcion(nuevo_estado):
        # Disrupciones no existe todavía en esta sesión — se documenta la
        # intención en vez de simular un disparo real (ver errores-conocidos.md).
        detalle["notificacion"] = "pendiente_de_modulo_disrupciones"

    await AuditService().insertar(
        "forzar_estado",
        "vuelos_catalogo",
        usuario_id=usuario["id"],
        registro_id=vuelo_id,
        detalle=detalle,
    )
    return JSONResponse({"id": actualizado["id"], "estado": actualizado["estado"]})


async def _contexto_config_asientos(usuario: dict, **extra) -> dict:
    repo = VuelosRepository()
    recargo = await repo.config("disponibilidad_asientos.recargo_premium")
    pct = await repo.config("disponibilidad_asientos.pct_filas_premium")
    horas = await repo.config("disponibilidad_asientos.horas_antes_checkin_gratis")
    contexto = await nav_context(usuario)
    contexto.update(
        {
            "recargo_premium": float(recargo) if recargo else DEFAULT_RECARGO_PREMIUM,
            # se muestra en % (0-100) en el formulario, se guarda como fracción (0-1)
            "pct_filas_premium_pct": (float(pct) if pct else DEFAULT_PCT_FILAS_PREMIUM) * 100,
            "horas_antes_checkin_gratis": float(horas) if horas else DEFAULT_HORAS_CHECKIN_GRATIS,
        }
    )
    contexto.update(extra)
    return contexto


@router.get("/config-asientos")
async def config_asientos_form(request: Request, usuario: dict = Depends(_PERMISO_CONFIG)):
    contexto = await _contexto_config_asientos(usuario)
    return templates.TemplateResponse(request, "backoffice/config_asientos.html", contexto)


@router.post("/config-asientos")
async def config_asientos_submit(
    request: Request,
    recargo_premium: float = Form(...),
    pct_filas_premium_pct: float = Form(...),
    usuario: dict = Depends(_PERMISO_CONFIG),
):
    if recargo_premium < 0 or not (0 <= pct_filas_premium_pct <= 100):
        contexto = await _contexto_config_asientos(
            usuario, error="El recargo no puede ser negativo y el % de filas premium debe estar entre 0 y 100."
        )
        return templates.TemplateResponse(request, "backoffice/config_asientos.html", contexto, status_code=400)

    repo = VuelosRepository()
    await repo.actualizar_config("disponibilidad_asientos.recargo_premium", str(recargo_premium), usuario["id"])
    await repo.actualizar_config(
        "disponibilidad_asientos.pct_filas_premium", str(pct_filas_premium_pct / 100), usuario["id"]
    )
    await AuditService().insertar(
        "editar",
        "configuracion_sistema",
        usuario_id=usuario["id"],
        detalle={"categoria": "disponibilidad_asientos", "recargo_premium": recargo_premium, "pct_filas_premium_pct": pct_filas_premium_pct},
    )
    return RedirectResponse(
        "/backoffice/vuelos/config-asientos?mensaje=Configuración+de+asientos+premium+actualizada", status_code=303
    )


@router.post("/config-checkin")
async def config_checkin_submit(
    request: Request,
    horas_antes_checkin_gratis: float = Form(...),
    usuario: dict = Depends(_PERMISO_CONFIG),
):
    if horas_antes_checkin_gratis < 0:
        contexto = await _contexto_config_asientos(usuario, error="Las horas no pueden ser negativas.")
        return templates.TemplateResponse(request, "backoffice/config_asientos.html", contexto, status_code=400)

    repo = VuelosRepository()
    await repo.actualizar_config(
        "disponibilidad_asientos.horas_antes_checkin_gratis", str(horas_antes_checkin_gratis), usuario["id"]
    )
    await AuditService().insertar(
        "editar",
        "configuracion_sistema",
        usuario_id=usuario["id"],
        detalle={"categoria": "disponibilidad_asientos", "horas_antes_checkin_gratis": horas_antes_checkin_gratis},
    )
    return RedirectResponse(
        "/backoffice/vuelos/config-asientos?mensaje=Ventana+de+check-in+gratuito+actualizada", status_code=303
    )


async def _contexto_rotacion_cabina(usuario: dict, **extra) -> dict:
    repo = VuelosRepository()
    rutas_valor = await repo.config("vuelos.google_flights_rutas_por_corrida")
    clases_valor = await repo.config("vuelos.google_flights_clases_activas")
    activas = {c.strip() for c in clases_valor.split(",")} if clases_valor else set(CLASES_CABINA)
    contexto = await nav_context(usuario)
    contexto.update(
        {
            "rutas_por_corrida": int(rutas_valor) if rutas_valor else RUTAS_POR_CORRIDA_DEFAULT,
            "clases_disponibles": CLASES_CABINA,
            "clases_activas": activas,
        }
    )
    contexto.update(extra)
    return contexto


@router.get("/config-rotacion-cabina")
async def config_rotacion_cabina_form(request: Request, usuario: dict = Depends(_PERMISO_CONFIG)):
    contexto = await _contexto_rotacion_cabina(usuario)
    return templates.TemplateResponse(request, "backoffice/config_rotacion_cabina.html", contexto)


@router.post("/config-rotacion-cabina")
async def config_rotacion_cabina_submit(
    request: Request,
    rutas_por_corrida: int = Form(...),
    clases_activas: list[str] = Form([]),
    usuario: dict = Depends(_PERMISO_CONFIG),
):
    clases_validas = [c for c in clases_activas if c in CLASES_CABINA]
    if rutas_por_corrida < 1:
        contexto = await _contexto_rotacion_cabina(usuario, error="Debe procesarse al menos 1 ruta por corrida.")
        return templates.TemplateResponse(request, "backoffice/config_rotacion_cabina.html", contexto, status_code=400)
    if not clases_validas:
        # Guarda vacío != "usa el default" en enriquecimiento_service (una
        # clave vacía cae al fallback de las 3 clases) — se bloquea acá para
        # que "ninguna clase" sea un estado explícito imposible, no un bug
        # silencioso que reactive todo sin que el admin lo pida.
        contexto = await _contexto_rotacion_cabina(usuario, error="Debe quedar al menos una clase de cabina activa.")
        return templates.TemplateResponse(request, "backoffice/config_rotacion_cabina.html", contexto, status_code=400)

    repo = VuelosRepository()
    await repo.actualizar_config("vuelos.google_flights_rutas_por_corrida", str(rutas_por_corrida), usuario["id"])
    await repo.actualizar_config(
        "vuelos.google_flights_clases_activas", ",".join(clases_validas), usuario["id"]
    )
    await AuditService().insertar(
        "editar",
        "configuracion_sistema",
        usuario_id=usuario["id"],
        detalle={
            "categoria": "vuelos",
            "google_flights_rutas_por_corrida": rutas_por_corrida,
            "google_flights_clases_activas": clases_validas,
        },
    )
    return RedirectResponse(
        "/backoffice/vuelos/config-rotacion-cabina?mensaje=Rotación+de+Google+Flights+actualizada", status_code=303
    )
