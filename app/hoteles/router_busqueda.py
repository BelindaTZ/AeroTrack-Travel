"""RF-HOT-001,002,003,006,007,008 (CU-O54,O55,O56,O57,O58,O59) — buscar
hoteles por destino, ver detalle (category_scores, servicios, reseñas,
cargos locales cuando la ciudad está cubierta), filtrar (instantáneo,
REG-J9) y comparar habitaciones reembolsables vs. no reembolsables.

RF-HOT-006 (CU-O57, seleccionar habitación) se resuelve posteando directo
a `/carrito/agregar` (Carrito) — mismo criterio de reutilización que
Autos/Actividades/Cruceros, sin `router_seleccion.py` propio.

**Fuera de alcance de esta ronda** (ver `checklist.md`): RF-HOT-009 (pago
diferido, CU-O60) y el clima del destino — ninguno tiene código todavía."""

from fastapi import APIRouter, Depends, Request

from app.hoteles.repositories.catalogo_reader import CatalogoHotelesReader
from app.hoteles.repositories.hoteles_repo import HotelesRepository
from app.hoteles.schemas import HotelBusquedaOut
from app.hoteles.services.comparacion_service import DemasiadosHoteles, comparar_hoteles
from app.hoteles.services.disponibilidad_service import cupo_minimo_en_rango
from app.paquetes.repositories.paquetes_repo import PaquetesRepository
from app.paquetes.services.paquete_service import (
    ReservaNoEncontrada,
    SinPermiso,
    combinacion_de,
    verificar_propiedad,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import usuario_opcional
from app.shared.busqueda_reciente import registrar_busqueda_reciente
from app.shared.google_apis.maps_embed import url_mapa_punto
from app.shared.rango_fechas import fechas_rango
from app.shared.templating import templates

router = APIRouter(prefix="/hoteles")

_MESES_ES = {
    "01": "enero", "02": "febrero", "03": "marzo", "04": "abril",
    "05": "mayo", "06": "junio", "07": "julio", "08": "agosto",
    "09": "septiembre", "10": "octubre", "11": "noviembre", "12": "diciembre",
}


def _mes_legible(mes: str) -> str:
    if mes == "todos":
        return "todos los meses"
    anio, mm = mes.split("-")
    return f"{_MESES_ES.get(mm, mm)} {anio}"


async def opciones_mes(catalogo: CatalogoHotelesReader) -> list[dict]:
    return [{"valor": m, "legible": _mes_legible(m)} for m in await catalogo.meses_disponibles()]


async def _ahorro_paquete_preview(usuario: dict | None, paquete_id: str | None) -> dict | None:
    """Si se está armando un paquete (`?paquete_id=` en la URL, ver
    detalle_hotel.html/paquetes_armar.html), calcula CUÁNTO se ahorraría
    con la combinación resultante de sumar un hotel — mismo % real de
    `tipos_paquete_descuento` que usa `calcular_resumen`, solo que acá es
    una previsualización (el hotel todavía no se agregó a la reserva).
    Nunca revienta la búsqueda: si el paquete no existe, no es del usuario,
    o no hay sesión, simplemente no hay previsualización."""
    if not paquete_id or not usuario:
        return None
    reservas_repo = ReservasRepository()
    pasajero = await reservas_repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        return None
    try:
        await verificar_propiedad(reservas_repo, pasajero["id"], paquete_id)
    except (ReservaNoEncontrada, SinPermiso):
        return None

    items = await reservas_repo.items_de_reserva(paquete_id)
    tipos_existentes = {i["tipo_producto"] for i in items}
    subtotal_existente = sum(i.get("precio_final") or 0.0 for i in items)
    combinacion = combinacion_de(tipos_existentes | {"hotel"})
    descuento = await PaquetesRepository().descuento_por_combinacion(combinacion)
    if not descuento:
        return None
    return {"porcentaje": descuento["porcentaje_descuento"], "subtotal_existente": subtotal_existente}


def _parse_float(valor: str | None) -> float | None:
    """Los filtros numéricos opcionales se reciben como string (no `float`
    nativo de FastAPI): el form oculto de filtros de la sidebar siempre
    manda estos tres campos, aunque estén vacíos — con un tipo `float`
    nativo, FastAPI rechaza "" con 422 en vez de tratarlo como "sin valor"
    (mismo fix que en vuelos/router_busqueda.py)."""
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _filtrar(hoteles: list[dict], estrellas_min: float | None, precio_max: float | None, calificacion_min: float | None) -> list[dict]:
    resultado = hoteles
    if estrellas_min is not None:
        resultado = [h for h in resultado if (h.get("estrellas") or 0) >= estrellas_min]
    if precio_max is not None:
        resultado = [h for h in resultado if h.get("precio_desde") is not None and h["precio_desde"] <= precio_max]
    if calificacion_min is not None:
        resultado = [h for h in resultado if (h.get("calificacion_promedio") or 0) >= calificacion_min]
    return resultado


async def _con_precio_desde(catalogo: CatalogoHotelesReader, hotel: dict) -> dict:
    tarifas = await catalogo.tarifas_de_hotel(hotel["id"])
    precios = [t["precio_final"] for t in tarifas if t.get("precio_final")]
    return {**hotel, "precio_desde": min(precios) if precios else None}


async def _con_disponibilidad_en_rango(
    catalogo: CatalogoHotelesReader, hotel: dict, checkin: str, checkout: str, habitaciones: int
) -> dict | None:
    """RF-HOT-004 (gap real cerrado 2026-07-29) — antes checkin/checkout
    eran cosméticos: reemplaza `_con_precio_desde` cuando el pasajero SÍ
    pidió fechas. `None` si ninguna tarifa del hotel tiene cupo real para
    TODO el rango (nunca noches parciales) y `habitaciones` a la vez —
    el llamador descarta el hotel del listado en ese caso."""
    tarifas = await catalogo.tarifas_de_hotel(hotel["id"])
    calificadas = []
    for t in tarifas:
        cupo = await cupo_minimo_en_rango(t["id"], checkin, checkout)
        if cupo is not None and cupo >= habitaciones:
            calificadas.append(t)
    if not calificadas:
        return None
    precio_desde = min(t["precio_final"] for t in calificadas if t.get("precio_final"))
    return {**hotel, "precio_desde": precio_desde}


def _opciones_ciudades(ciudades: list[dict]) -> list[dict]:
    return [{"valor": c["ciudad"], "principal": c["ciudad"], "secundario": c["pais"] or None} for c in ciudades]


async def _formulario_vacio(request: Request, usuario: dict | None, **filtros_extra) -> object:
    catalogo = CatalogoHotelesReader()
    ciudades = _opciones_ciudades(await catalogo.ciudades_disponibles())
    meses = await opciones_mes(catalogo)
    filtros = {
        "ciudad": "", "checkin": "", "checkout": "", "mes": "",
        "huespedes": 1, "habitaciones": 1, "estrellas_min": "", "precio_max": "", "calificacion_min": "",
    }
    filtros.update(filtros_extra)
    return templates.TemplateResponse(
        request, "buscar_hoteles.html",
        {"resultados": None, "ciudades": ciudades, "meses": meses, "filtros": filtros, "usuario": usuario},
    )


@router.get("/buscar")
async def buscar(
    request: Request,
    ciudad: str | None = None,
    checkin: str | None = None,
    checkout: str | None = None,
    mes: str | None = None,
    huespedes: int = 1,
    habitaciones: int = 1,
    estrellas_min: str | None = None,
    precio_max: str | None = None,
    calificacion_min: str | None = None,
    paquete_id: str | None = None,
    usuario: dict | None = Depends(usuario_opcional),
):
    estrellas_min_val = _parse_float(estrellas_min)
    precio_max_val = _parse_float(precio_max)
    calificacion_min_val = _parse_float(calificacion_min)
    # "aún no definí la fecha" (REG-T3) — `mes` es mutuamente excluyente
    # con checkin/checkout, mismo criterio que vuelos. A diferencia de
    # vuelos (donde un mes SÍ filtra, porque cada vuelo es una fecha
    # puntual), un hotel no tiene "el mes correcto" para chequear cupo
    # real sin asumir una duración de estadía — se mantiene el listado
    # cosmético de siempre, `mes` solo se usa para el aviso en pantalla,
    # nunca se fabrica un rango de fechas.
    if mes:
        checkin = checkout = None

    if not ciudad:
        return await _formulario_vacio(
            request, usuario, estrellas_min=estrellas_min_val or "", precio_max=precio_max_val or "", calificacion_min=calificacion_min_val or ""
        )

    await registrar_busqueda_reciente(
        usuario, "hotel",
        {"ciudad": ciudad, "checkin": checkin or "", "checkout": checkout or "", "huespedes": huespedes},
    )
    catalogo = CatalogoHotelesReader()
    hoteles = await catalogo.buscar_por_ciudad(ciudad)
    if checkin and checkout:
        # RF-HOT-004 — con fechas, el listado refleja disponibilidad real
        # (nunca noches parciales); sin fechas, cosmético como antes
        # (compatible hacia atrás con la búsqueda sin fecha fija, REG-T3).
        con_disponibilidad = [
            await _con_disponibilidad_en_rango(catalogo, h, checkin, checkout, habitaciones) for h in hoteles
        ]
        hoteles = [h for h in con_disponibilidad if h is not None]
    else:
        hoteles = [await _con_precio_desde(catalogo, h) for h in hoteles]
    hoteles = _filtrar(hoteles, estrellas_min_val, precio_max_val, calificacion_min_val)

    noches = len(fechas_rango(checkin, checkout)) if checkin and checkout else None
    resultados = [
        HotelBusquedaOut(
            id=h["id"], nombre=h["nombre"], ciudad=h["ciudad"], estrellas=h.get("estrellas"),
            calificacion_promedio=h.get("calificacion_promedio"), cantidad_resenas=h.get("cantidad_resenas"),
            precio_desde=h.get("precio_desde"), imagen_principal=h.get("imagen_principal"), noches=noches,
        )
        for h in hoteles
    ]
    resultados.sort(key=lambda r: r.precio_desde if r.precio_desde is not None else float("inf"))

    # Ahorro en vivo si se está armando un paquete (ver detalle en
    # `_ahorro_paquete_preview`) — % real, nunca inventado; `None` si no
    # aplica (sin paquete_id, sesión de invitado, o paquete ajeno).
    ahorro_paquete = await _ahorro_paquete_preview(usuario, paquete_id)
    ahorros_por_hotel: dict[str, float] = {}
    if ahorro_paquete:
        for r in resultados:
            if r.precio_desde is not None:
                total_preview = ahorro_paquete["subtotal_existente"] + r.precio_desde
                ahorros_por_hotel[r.id] = round(total_preview * ahorro_paquete["porcentaje"] / 100, 2)

    ciudades = _opciones_ciudades(await catalogo.ciudades_disponibles())
    meses = await opciones_mes(catalogo)

    return templates.TemplateResponse(
        request,
        "buscar_hoteles.html",
        {
            "resultados": resultados,
            "ciudades": ciudades,
            "meses": meses,
            "busqueda_mes_legible": _mes_legible(mes) if mes else None,
            "paquete_id": paquete_id,
            "ahorro_paquete_porcentaje": ahorro_paquete["porcentaje"] if ahorro_paquete else None,
            "ahorros_por_hotel": ahorros_por_hotel,
            "filtros": {
                "ciudad": ciudad, "checkin": checkin or "", "checkout": checkout or "", "mes": mes or "",
                "huespedes": huespedes, "habitaciones": habitaciones,
                "estrellas_min": estrellas_min_val or "", "precio_max": precio_max_val or "", "calificacion_min": calificacion_min_val or "",
            },
            "usuario": usuario,
        },
    )


@router.get("/comparar")
async def comparar(request: Request, ids: str = "", usuario: dict | None = Depends(usuario_opcional)):
    """CU-T09 (RF-HOT-T01) — de cara al pasajero, sin RBAC interno (la spec
    lo confirma explícitamente: no requiere rol de backoffice). Tiene que
    registrarse ANTES de /{hotel_id} — si no, "comparar" se interpreta como
    un hotel_id (Starlette matchea rutas en orden de declaración) y esto
    devuelve 404 en vez de la comparación."""
    ids_lista = [i for i in ids.split(",") if i]
    try:
        hoteles = await comparar_hoteles(ids_lista)
    except DemasiadosHoteles as exc:
        return templates.TemplateResponse(
            request, "comparar_hoteles.html",
            {"hoteles": [], "usuario": usuario, "error": str(exc)},
            status_code=400,
        )
    return templates.TemplateResponse(
        request, "comparar_hoteles.html", {"hoteles": hoteles, "usuario": usuario, "error": None}
    )


@router.get("/{hotel_id}")
async def detalle(
    request: Request,
    hotel_id: str,
    checkin: str | None = None,
    checkout: str | None = None,
    habitaciones: int = 1,
    usuario: dict | None = Depends(usuario_opcional),
):
    repo = HotelesRepository()  # solo para lectura CONFIG (maps_embed_api_key)
    catalogo = CatalogoHotelesReader()
    hotel = await catalogo.obtener_hotel(hotel_id)
    if hotel is None:
        return templates.TemplateResponse(request, "detalle_hotel.html", {"hotel": None, "usuario": usuario}, status_code=404)

    tarifas = await catalogo.tarifas_de_hotel(hotel_id)
    noches = None
    if checkin and checkout:
        # RF-HOT-004 — con fechas seleccionadas, `cupos_disponibles` pasa a
        # ser el cupo real MÍNIMO del rango completo (nunca el valor
        # congelado de una sola noche/snapshot) y se suma `precio_total`
        # (precio por noche × noches) — antes esto no existía, el precio
        # era el mismo sin importar cuántas noches se pidieran.
        noches = len(fechas_rango(checkin, checkout))
        tarifas_out = []
        for t in tarifas:
            cupo = await cupo_minimo_en_rango(t["id"], checkin, checkout)
            precio_total = (t["precio_final"] * noches) if t.get("precio_final") else None
            tarifas_out.append({**t, "cupos_disponibles": cupo, "precio_total": precio_total})
        tarifas = tarifas_out
    else:
        tarifas = [{**t, "cupos_disponibles": None, "precio_total": None} for t in tarifas]
    tarifas.sort(key=lambda t: t.get("precio_final") or 0)
    resenas = await catalogo.resenas_de_hotel(hotel_id)
    cargos_locales = await catalogo.cargos_locales_de_ciudad(hotel["ciudad"])

    mapa_url = None
    if hotel.get("latitud") and hotel.get("longitud"):
        api_key = await repo.config("google_apis.maps_embed_api_key")
        if api_key:
            mapa_url = url_mapa_punto(hotel["latitud"], hotel["longitud"], api_key)

    return templates.TemplateResponse(
        request,
        "detalle_hotel.html",
        {
            "hotel": hotel, "tarifas": tarifas, "resenas": resenas, "cargos_locales": cargos_locales,
            "mapa_url": mapa_url, "usuario": usuario,
            "filtros": {"checkin": checkin or "", "checkout": checkout or "", "habitaciones": habitaciones, "noches": noches},
        },
    )
