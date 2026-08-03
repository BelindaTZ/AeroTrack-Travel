"""RF-VUE-001,002 — buscar vuelos disponibles, ver detalle y niveles de tarifa."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.paquetes.repositories.paquetes_repo import PaquetesRepository
from app.vuelos.repositories.catalogo_reader import CatalogoVuelosReader
from app.vuelos.repositories.dims_reader import resolver_aeropuerto
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.schemas import NivelTarifaOut, VueloBusquedaOut
from app.vuelos.services.analitica_ruta_service import obtener_analitica_ruta
from app.vuelos.services.asientos_service import obtener_o_generar_mapa
from app.seguridad.services.session_service import usuario_opcional
from app.shared.busqueda_reciente import registrar_busqueda_reciente
from app.shared.cupo_service import cupos_vigentes
from app.shared.templating import templates

router = APIRouter(prefix="/vuelos")

# RF-VUE-007 — 4 franjas horarias reales, filtrado por selección múltiple
# (checkboxes: ninguna marcada o todas marcadas = sin filtro, igual que
# cualquier subconjunto intermedio actúa como OR entre franjas).
_BUCKETS_HORARIO = {
    "madrugada": ("00:00", "06:00"),
    "manana": ("06:00", "12:00"),
    "tarde": ("12:00", "18:00"),
    "noche": ("18:00", "23:59"),
}

_MESES_ES = {
    "01": "enero", "02": "febrero", "03": "marzo", "04": "abril",
    "05": "mayo", "06": "junio", "07": "julio", "08": "agosto",
    "09": "septiembre", "10": "octubre", "11": "noviembre", "12": "diciembre",
}


def _mes_legible(mes: str) -> str:
    anio, mm = mes.split("-")
    return f"{_MESES_ES.get(mm, mm)} {anio}"


async def opciones_mes(catalogo: CatalogoVuelosReader) -> list[dict]:
    return [{"valor": m, "legible": _mes_legible(m)} for m in await catalogo.meses_disponibles()]


async def opciones_aeropuertos(catalogo: CatalogoVuelosReader) -> list[dict]:
    """`[{"valor": codigo, "principal": legible, "secundario": codigo}]`
    para el selector de origen/destino — solo aeropuertos con vuelos
    reales en el catálogo, nunca una lista global inventada."""
    codigos = await catalogo.codigos_aeropuertos_disponibles()
    return [
        {"valor": c, "principal": await resolver_aeropuerto(c), "secundario": c}
        for c in codigos
    ]


async def _formulario_vacio(request: Request, usuario: dict | None, **filtros_extra) -> object:
    catalogo = CatalogoVuelosReader()
    aerolineas = await catalogo.listar_aerolineas_activas()
    aeropuertos = await opciones_aeropuertos(catalogo)
    meses = await opciones_mes(catalogo)
    filtros = {
        "origen": "", "destino": "", "fecha": "", "mes": "", "pasajeros": 1, "aerolinea_id": "",
        "horario": [], "equipaje": False, "orden": "precio", "precio_max": None,
    }
    filtros.update(filtros_extra)
    return templates.TemplateResponse(
        request,
        "buscar_vuelos.html",
        {
            "resultados": None, "aerolineas": aerolineas, "aeropuertos": aeropuertos,
            "meses": meses, "filtros": filtros, "usuario": usuario,
        },
    )


@router.get("/buscar")
async def buscar(
    request: Request,
    origen: str | None = None,
    destino: str | None = None,
    fecha: str | None = None,
    mes: str | None = None,
    pasajeros: int = Query(1, ge=1, le=9),
    aerolinea_id: str | None = None,
    horario: list[str] = Query([]),
    equipaje: bool = False,
    precio_max: str | None = None,
    orden: str = "precio",
    usuario: dict | None = Depends(usuario_opcional),
):
    # `fecha`/`precio_max` se reciben como string (no `date`/`float` de
    # FastAPI): el form oculto de filtros (sidebar) siempre manda estos
    # campos, aunque estén vacíos — con un tipo `date`/`float` nativo,
    # FastAPI rechaza "" con 422 en vez de tratarlo como "sin valor".
    fecha_obj: date | None = None
    if fecha:
        try:
            fecha_obj = date.fromisoformat(fecha)
        except ValueError:
            fecha_obj = None
    precio_max_val: float | None = None
    if precio_max:
        try:
            precio_max_val = float(precio_max)
        except ValueError:
            precio_max_val = None

    # `mes` ("YYYY-MM") es la alternativa a `fecha` para "aún no definí la
    # fecha" — `CatalogoVuelosReader.buscar` ya matchea por prefijo de
    # `fecha_salida`, así que un mes funciona igual que una fecha exacta,
    # solo que trae vuelos de varios días en vez de uno.
    fecha_busqueda = fecha_obj.isoformat() if fecha_obj else (mes or None)
    if not (origen and destino and fecha_busqueda):
        return await _formulario_vacio(request, usuario, orden=orden)

    origen, destino = origen.upper(), destino.upper()
    await registrar_busqueda_reciente(
        usuario, "vuelo", {"origen": origen, "destino": destino, "fecha": fecha_busqueda, "pasajeros": pasajeros}
    )
    repo = VuelosRepository()  # solo para lecturas CONFIG (niveles_tarifa)
    catalogo = CatalogoVuelosReader()  # STAGING (vuelos_catalogo/tarifas_vuelo/aerolineas)
    vuelos = await catalogo.buscar(origen, destino, fecha_busqueda, aerolinea_id or None)

    # RF-VUE-007 — franja horaria: multi-select tipo OR entre las franjas
    # marcadas; ninguna marcada equivale a "todas" (sin filtro), no a cero
    # resultados — mismo criterio que la sidebar de aerolíneas.
    horarios_validos = [h for h in horario if h in _BUCKETS_HORARIO]
    if horarios_validos:
        vuelos = [
            v for v in vuelos
            if any(
                _BUCKETS_HORARIO[h][0] <= v["hora_salida_programada"] < _BUCKETS_HORARIO[h][1]
                for h in horarios_validos
            )
        ]

    # RF-VUE-007 — equipaje: "escalas" no se ofrece como filtro porque el
    # modelo no tiene ese concepto (todo vuelo es un solo tramo, confirmado
    # en google_flights_client.py) — no hay nada real que filtrar ahí.
    niveles = await repo.listar_niveles_tarifa()
    niveles_con_equipaje = {n["id"] for n in niveles if n.get("equipaje_incluido")}

    resultados: list[VueloBusquedaOut] = []
    for v in vuelos:
        tarifas = await catalogo.tarifas_de_vuelo(v["id"])
        if not tarifas:
            continue
        tiene_equipaje = any(t["nivel_tarifa_id"] in niveles_con_equipaje for t in tarifas)
        if equipaje and not tiene_equipaje:
            continue
        aerolinea = await catalogo.obtener_aerolinea(v["aerolinea_id"])
        resultados.append(
            VueloBusquedaOut(
                id=v["id"],
                numero_vuelo=v["numero_vuelo"],
                aerolinea_nombre=aerolinea["nombre"],
                origen_codigo=v["origen_codigo"],
                destino_codigo=v["destino_codigo"],
                origen_legible=await resolver_aeropuerto(v["origen_codigo"]),
                destino_legible=await resolver_aeropuerto(v["destino_codigo"]),
                fecha_salida=v["fecha_salida"][:10],
                hora_salida_programada=v["hora_salida_programada"],
                hora_llegada_programada=v["hora_llegada_programada"],
                duracion_min=v.get("duracion_min"),
                precio_desde=min(t["precio_final"] for t in tarifas),
                equipaje_incluido=tiene_equipaje,
            )
        )

    # Rango de precio disponible ANTES de aplicar el filtro de precio en sí
    # (aerolínea/horario/equipaje ya aplicados arriba) — así el slider
    # siempre refleja el techo real de esta búsqueda, no el resultado ya
    # recortado por `precio_max`.
    precio_min_disponible = min((r.precio_desde for r in resultados), default=0.0)
    precio_max_disponible = max((r.precio_desde for r in resultados), default=0.0)

    if precio_max_val is not None:
        resultados = [r for r in resultados if r.precio_desde <= precio_max_val]

    if orden == "duracion":
        resultados.sort(key=lambda r: r.duracion_min if r.duracion_min is not None else 0)
    else:
        resultados.sort(key=lambda r: r.precio_desde)

    # RF-VUE-008 (CU-O51) — predicción de precio de la ruta/fecha buscada,
    # si Google Flights ya la refrescó (puede no existir, no bloquea la
    # búsqueda). Solo tiene sentido con fecha exacta — con búsqueda por mes
    # habría varias fechas candidatas y mostrar una sola sería ambiguo.
    prediccion = await catalogo.prediccion_por_ruta_fecha(origen, destino, fecha_obj.isoformat()) if fecha_obj else None

    # Cross-sell a Paquetes: solo se muestra si existe de verdad un
    # descuento activo para "vuelo+hotel" en `tipos_paquete_descuento" — el
    # % nunca se inventa. El paquete en sí se arma desde el detalle del
    # vuelo (botón "Arma un paquete con este vuelo", ver detalle_vuelo.html),
    # porque recién ahí hay una tarifa elegida — acá es solo el aviso.
    descuento_vuelo_hotel = None
    if resultados:
        descuento_vuelo_hotel = await PaquetesRepository().descuento_por_combinacion("vuelo+hotel")

    aerolineas = await catalogo.listar_aerolineas_activas()
    aeropuertos = await opciones_aeropuertos(catalogo)
    meses = await opciones_mes(catalogo)

    return templates.TemplateResponse(
        request,
        "buscar_vuelos.html",
        {
            "resultados": resultados,
            "aerolineas": aerolineas,
            "aeropuertos": aeropuertos,
            "meses": meses,
            "filtros": {
                "origen": origen, "destino": destino,
                "fecha": fecha_obj.isoformat() if fecha_obj else "", "mes": mes or "",
                "pasajeros": pasajeros, "aerolinea_id": aerolinea_id or "",
                "horario": horarios_validos, "equipaje": equipaje, "orden": orden,
                "precio_max": precio_max_val,
            },
            "busqueda_mes_legible": _mes_legible(mes) if (mes and not fecha_obj) else None,
            "precio_min_disponible": precio_min_disponible,
            "precio_max_disponible": precio_max_disponible,
            "prediccion": prediccion,
            "descuento_vuelo_hotel": descuento_vuelo_hotel,
            "usuario": usuario,
        },
    )


@router.get("/analitica-ruta")
async def analitica_ruta(origen: str, destino: str):
    """DB-04 — Diferenciador Analítico de Vuelos. Se declara antes de
    `/{vuelo_id}` para no quedar capturada por esa ruta con parámetro."""
    return JSONResponse(obtener_analitica_ruta(origen, destino))


@router.get("/{vuelo_id}")
async def detalle(request: Request, vuelo_id: str, usuario: dict | None = Depends(usuario_opcional)):
    repo = VuelosRepository()  # solo para lecturas CONFIG (niveles_tarifa/politicas_reembolso)
    catalogo = CatalogoVuelosReader()
    vuelo = await catalogo.obtener_vuelo(vuelo_id)
    if vuelo is None:
        return templates.TemplateResponse(request, "detalle_vuelo.html", {"vuelo": None, "usuario": usuario}, status_code=404)

    aerolinea = await catalogo.obtener_aerolinea(vuelo["aerolinea_id"])
    tarifas = await catalogo.tarifas_de_vuelo(vuelo_id)
    # `tarifas_vuelo.cupos_disponibles` queda congelado en PocketBase desde
    # que el cupo real se decrementa en MinIO (ver app.shared.cupo_service)
    # — sin este overlay, el detalle mostraría para siempre el valor
    # sembrado en vez del cupo ya reservado por otras compras.
    cupos_reales = await cupos_vigentes("tarifas_vuelo")

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
                cupos_disponibles=cupos_reales.get(t["id"], t["cupos_disponibles"]),
                politica_nombre=politica["nombre"],
                politica_condiciones=politica["condiciones"],
                politica_porcentaje_reembolso=politica["porcentaje_reembolso"],
                politica_ventana_horas=politica["ventana_horas"],
                clase_cabina=t.get("clase_cabina") or "economy",
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
            "usuario": usuario,
        },
    )


@router.get("/{vuelo_id}/asientos")
async def mapa_asientos(vuelo_id: str):
    """RF-VUE-011 (CU-O115) — mapa de asientos del vuelo, generado bajo
    demanda (idempotente) si todavía no existe. Consumido por el picker de
    asiento en el checkout de Reservas."""
    repo = VuelosRepository()
    vuelo = await repo.obtener_vuelo(vuelo_id)
    if vuelo is None:
        return JSONResponse({"detail": "Vuelo no encontrado"}, status_code=404)

    asientos = await obtener_o_generar_mapa(vuelo_id, repo)
    return JSONResponse(
        [
            {
                "id": a["id"],
                "fila": a["fila"],
                "columna": a["columna"],
                "tipo_asiento": a["tipo_asiento"],
                "es_premium": a["es_premium"],
                "recargo": a["recargo"],
                "disponible": a["disponible"],
            }
            for a in asientos
        ]
    )
