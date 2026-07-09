"""RF-VUE-001,002 — buscar vuelos disponibles, ver detalle y niveles de tarifa."""

from datetime import date

from fastapi import APIRouter, Query, Request

from app.vuelos.repositories.dims_reader import resolver_aeropuerto
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.schemas import NivelTarifaOut, VueloBusquedaOut
from app.shared.templating import templates

router = APIRouter(prefix="/vuelos")

_BUCKETS_HORARIO = {
    "manana": ("00:00", "12:00"),
    "tarde": ("12:00", "18:00"),
    "noche": ("18:00", "23:59"),
}


async def _formulario_vacio(request: Request, **filtros_extra) -> object:
    repo = VuelosRepository()
    aerolineas = await repo.listar_aerolineas_activas()
    codigos = await repo.codigos_aeropuertos_disponibles()
    aeropuertos = [{"codigo": c, "legible": await resolver_aeropuerto(c)} for c in codigos]
    filtros = {"origen": "", "destino": "", "fecha": "", "pasajeros": 1, "aerolinea_id": "", "horario": "", "orden": "precio"}
    filtros.update(filtros_extra)
    return templates.TemplateResponse(
        request,
        "buscar_vuelos.html",
        {"resultados": None, "aerolineas": aerolineas, "aeropuertos": aeropuertos, "filtros": filtros},
    )


@router.get("/buscar")
async def buscar(
    request: Request,
    origen: str | None = None,
    destino: str | None = None,
    fecha: date | None = None,
    pasajeros: int = Query(1, ge=1, le=9),
    aerolinea_id: str | None = None,
    horario: str = "",
    orden: str = "precio",
):
    if not (origen and destino and fecha):
        return await _formulario_vacio(request, orden=orden)

    origen, destino = origen.upper(), destino.upper()
    repo = VuelosRepository()
    vuelos = await repo.buscar(origen, destino, fecha.isoformat(), aerolinea_id or None)

    if horario in _BUCKETS_HORARIO:
        desde, hasta = _BUCKETS_HORARIO[horario]
        vuelos = [v for v in vuelos if desde <= v["hora_salida_programada"] < hasta]

    resultados: list[VueloBusquedaOut] = []
    for v in vuelos:
        tarifas = await repo.tarifas_de_vuelo(v["id"])
        if not tarifas:
            continue
        aerolinea = await repo.obtener_aerolinea(v["aerolinea_id"])
        resultados.append(
            VueloBusquedaOut(
                id=v["id"],
                numero_vuelo=v["numero_vuelo"],
                aerolinea_nombre=aerolinea["nombre"],
                origen_legible=await resolver_aeropuerto(v["origen_codigo"]),
                destino_legible=await resolver_aeropuerto(v["destino_codigo"]),
                fecha_salida=v["fecha_salida"][:10],
                hora_salida_programada=v["hora_salida_programada"],
                hora_llegada_programada=v["hora_llegada_programada"],
                duracion_min=v.get("duracion_min"),
                precio_desde=min(t["precio_final"] for t in tarifas),
            )
        )

    if orden == "duracion":
        resultados.sort(key=lambda r: r.duracion_min if r.duracion_min is not None else 0)
    else:
        resultados.sort(key=lambda r: r.precio_desde)

    aerolineas = await repo.listar_aerolineas_activas()
    codigos = await repo.codigos_aeropuertos_disponibles()
    aeropuertos = [{"codigo": c, "legible": await resolver_aeropuerto(c)} for c in codigos]

    return templates.TemplateResponse(
        request,
        "buscar_vuelos.html",
        {
            "resultados": resultados,
            "aerolineas": aerolineas,
            "aeropuertos": aeropuertos,
            "filtros": {
                "origen": origen, "destino": destino, "fecha": fecha.isoformat(),
                "pasajeros": pasajeros, "aerolinea_id": aerolinea_id or "",
                "horario": horario, "orden": orden,
            },
        },
    )


@router.get("/{vuelo_id}")
async def detalle(request: Request, vuelo_id: str):
    repo = VuelosRepository()
    vuelo = await repo.obtener_vuelo(vuelo_id)
    if vuelo is None:
        return templates.TemplateResponse(request, "detalle_vuelo.html", {"vuelo": None}, status_code=404)

    aerolinea = await repo.obtener_aerolinea(vuelo["aerolinea_id"])
    tarifas = await repo.tarifas_de_vuelo(vuelo_id)

    niveles: list[NivelTarifaOut] = []
    for t in tarifas:
        nivel = await repo.nivel_tarifa(t["nivel_tarifa_id"])
        politica = await repo.politica_reembolso(nivel["politica_reembolso_id"])
        niveles.append(
            NivelTarifaOut(
                id=t["id"],
                nombre=nivel["nombre"],
                descripcion=nivel.get("descripcion"),
                equipaje_incluido=nivel["equipaje_incluido"],
                cambios_permitidos=nivel["cambios_permitidos"],
                precio_final=t["precio_final"],
                cupos_disponibles=t["cupos_disponibles"],
                politica_nombre=politica["nombre"],
                politica_condiciones=politica["condiciones"],
                politica_porcentaje_reembolso=politica["porcentaje_reembolso"],
                politica_ventana_horas=politica["ventana_horas"],
            )
        )
    niveles.sort(key=lambda n: n.precio_final)

    return templates.TemplateResponse(
        request,
        "detalle_vuelo.html",
        {
            "vuelo": vuelo,
            "aerolinea": aerolinea,
            "niveles": niveles,
            "origen_legible": await resolver_aeropuerto(vuelo["origen_codigo"]),
            "destino_legible": await resolver_aeropuerto(vuelo["destino_codigo"]),
        },
    )
