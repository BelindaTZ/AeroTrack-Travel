"""CU-T07 (monitor de estado del DAG de catálogo de vuelos, vía la REST API
de Airflow) y CU-T19 (dashboard de vuelos activos en monitoreo, lectura
directa de `vuelos_catalogo`)."""

from fastapi import APIRouter, Depends, Query, Request

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.disrupciones.services.riesgo_service import UMBRAL_RIESGO_PCT_DEFAULT, riesgo_estimado_por_aerolinea
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.csv_export import csv_response
from app.shared.minio_catalog_reader import fecha_publicacion, leer_coleccion
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates
from app.vuelos.repositories.airflow_client import AirflowNoDisponible, estado_dag
from app.vuelos.repositories.vuelos_repo import VuelosRepository

router = APIRouter(prefix="/backoffice/vuelos")

NIVELES_RIESGO = ["alto", "medio", "bajo"]


def _nivel_riesgo(riesgo_pct: float | None, umbral_alto: float) -> str | None:
    if riesgo_pct is None:
        return None
    if riesgo_pct >= umbral_alto:
        return "alto"
    if riesgo_pct >= umbral_alto / 2:
        return "medio"
    return "bajo"


async def _vuelos_activos_con_riesgo(
    aerolinea_id: str | None, ruta: str | None, nivel_riesgo: str | None
) -> list[dict]:
    """IS-11 — el riesgo se calcula en vivo por aerolínea (mismo cálculo que
    el simulador de disrupciones: 100 - OTP histórico), no está guardado por
    vuelo. `umbral_alto` es el mismo umbral configurable que dispara una
    disrupción real (`simulador_disrupciones.umbral_riesgo_pct`, default
    20%); "medio" es la mitad de ese umbral hacia arriba, "bajo" el resto —
    no hay una definición de negocio previa de estos tres niveles, así que
    se reutiliza el único umbral que sí existe en vez de inventar otro."""
    repo = VuelosRepository()
    vuelos = await repo.listar_activos(aerolinea_id=aerolinea_id or None, ruta=ruta or None)

    config_umbral = await DisrupcionesRepository().config("simulador_disrupciones.umbral_riesgo_pct")
    umbral_alto = float(config_umbral["valor"]) if config_umbral else UMBRAL_RIESGO_PCT_DEFAULT

    riesgo_por_iata = await riesgo_estimado_por_aerolinea()
    for v in vuelos:
        riesgo_pct = riesgo_por_iata.get(v.get("aerolinea_iata"))
        v["riesgo_pct"] = riesgo_pct
        v["nivel_riesgo"] = _nivel_riesgo(riesgo_pct, umbral_alto)

    if nivel_riesgo:
        vuelos = [v for v in vuelos if v["nivel_riesgo"] == nivel_riesgo]
    return vuelos


@router.get("/monitor-dag")
async def monitor_dag(
    request: Request,
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "ver")),
):
    try:
        info = await estado_dag()
        error = None
    except AirflowNoDisponible as exc:
        info = None
        error = str(exc)

    contexto = await nav_context(usuario)
    contexto.update({"info": info, "error": error})
    return templates.TemplateResponse(request, "backoffice/monitor_dag.html", contexto)


@router.get("/activos")
async def dashboard_activos(
    request: Request,
    aerolinea_id: str = Query(""),
    ruta: str = Query(""),
    nivel_riesgo: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "ver")),
):
    vuelos = await _vuelos_activos_con_riesgo(aerolinea_id, ruta, nivel_riesgo)
    pagina = paginar(vuelos, page)
    aerolineas = await VuelosRepository().listar_aerolineas_activas()

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "aerolineas": aerolineas,
            "niveles_riesgo": NIVELES_RIESGO,
            "filtros": {"aerolinea_id": aerolinea_id, "ruta": ruta, "nivel_riesgo": nivel_riesgo},
        }
    )
    return templates.TemplateResponse(request, "backoffice/dashboard_activos.html", contexto)


@router.get("/activos/exportar")
async def exportar_activos(
    aerolinea_id: str = Query(""),
    ruta: str = Query(""),
    nivel_riesgo: str = Query(""),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "ver")),
):
    vuelos = await _vuelos_activos_con_riesgo(aerolinea_id, ruta, nivel_riesgo)
    return csv_response(
        vuelos,
        [
            ("numero_vuelo", lambda v: v["numero_vuelo"]),
            ("aerolinea", lambda v: v["aerolinea_nombre"]),
            ("origen", lambda v: v["origen_codigo"]),
            ("destino", lambda v: v["destino_codigo"]),
            ("fecha_salida", lambda v: v.get("fecha_salida", "")[:10] if v.get("fecha_salida") else ""),
            ("hora_salida_programada", lambda v: v.get("hora_salida_programada", "")),
            ("estado", lambda v: v["estado"]),
            ("riesgo_pct", lambda v: v["riesgo_pct"] if v["riesgo_pct"] is not None else ""),
            ("nivel_riesgo", lambda v: v["nivel_riesgo"] or ""),
        ],
        "vuelos_activos.csv",
    )


async def _catalogo_publicado_filtrado(origen: str, destino: str, aerolinea_id: str) -> list[dict]:
    """IS-07 (auditoría de informes simples, sesión 2026-08-01) — lee el
    NDJSON real publicado en `aerotrack-travel-catalog` (`leer_coleccion`),
    NO la colección `vuelos_catalogo` de PocketBase que ya tiene panel en
    `/backoffice/vuelos` (WP-16) — son dos fuentes distintas, ver la nota
    de la auditoría original."""
    vuelos = await leer_coleccion("vuelos_catalogo")
    aerolineas = await leer_coleccion("aerolineas")
    nombre_por_id = {a["id"]: a["nombre"] for a in aerolineas}

    if origen:
        safe = origen.upper()
        vuelos = [v for v in vuelos if v.get("origen_codigo") == safe]
    if destino:
        safe = destino.upper()
        vuelos = [v for v in vuelos if v.get("destino_codigo") == safe]
    if aerolinea_id:
        vuelos = [v for v in vuelos if v.get("aerolinea_id") == aerolinea_id]

    vuelos_out = [{**v, "aerolinea_nombre": nombre_por_id.get(v.get("aerolinea_id"), "—")} for v in vuelos]
    vuelos_out.sort(key=lambda v: v.get("updated") or "", reverse=True)
    return vuelos_out


@router.get("/catalogo-publicado")
async def catalogo_publicado(
    request: Request,
    origen: str = Query(""),
    destino: str = Query(""),
    aerolinea_id: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "ver")),
):
    vuelos_out = await _catalogo_publicado_filtrado(origen, destino, aerolinea_id)
    pagina = paginar(vuelos_out, page, tamano_pagina=50)
    aerolineas_activas = await VuelosRepository().listar_aerolineas_activas()
    publicado = await fecha_publicacion("vuelos_catalogo")

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "aerolineas": aerolineas_activas,
            "fecha_publicacion": publicado,
            "filtros": {"origen": origen, "destino": destino, "aerolinea_id": aerolinea_id},
        }
    )
    return templates.TemplateResponse(request, "backoffice/catalogo_publicado.html", contexto)


@router.get("/catalogo-publicado/exportar")
async def exportar_catalogo_publicado(
    origen: str = Query(""),
    destino: str = Query(""),
    aerolinea_id: str = Query(""),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "ver")),
):
    vuelos_out = await _catalogo_publicado_filtrado(origen, destino, aerolinea_id)
    return csv_response(
        vuelos_out,
        [
            ("origen", lambda v: v.get("origen_codigo", "")),
            ("destino", lambda v: v.get("destino_codigo", "")),
            ("aerolinea", lambda v: v["aerolinea_nombre"]),
            ("precio_base", lambda v: v.get("precio_base", "")),
            ("fecha_actualizacion", lambda v: v.get("updated", "")),
        ],
        "catalogo_publicado_minio.csv",
    )
