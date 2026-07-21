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

from app.hoteles.repositories.hoteles_repo import HotelesRepository
from app.hoteles.schemas import HotelBusquedaOut
from app.seguridad.services.session_service import usuario_opcional
from app.shared.busqueda_reciente import registrar_busqueda_reciente
from app.shared.google_apis.maps_embed import url_mapa_punto
from app.shared.templating import templates

router = APIRouter(prefix="/hoteles")


def _filtrar(hoteles: list[dict], estrellas_min: float | None, precio_max: float | None, calificacion_min: float | None) -> list[dict]:
    resultado = hoteles
    if estrellas_min is not None:
        resultado = [h for h in resultado if (h.get("estrellas") or 0) >= estrellas_min]
    if precio_max is not None:
        resultado = [h for h in resultado if h.get("precio_desde") is not None and h["precio_desde"] <= precio_max]
    if calificacion_min is not None:
        resultado = [h for h in resultado if (h.get("calificacion_promedio") or 0) >= calificacion_min]
    return resultado


async def _con_precio_desde(repo: HotelesRepository, hotel: dict) -> dict:
    tarifas = await repo.tarifas_de_hotel(hotel["id"])
    precios = [t["precio_final"] for t in tarifas if t.get("precio_final")]
    return {**hotel, "precio_desde": min(precios) if precios else None}


async def _formulario_vacio(request: Request, usuario: dict | None, **filtros_extra) -> object:
    repo = HotelesRepository()
    ciudades = await repo.ciudades_disponibles()
    filtros = {"ciudad": "", "checkin": "", "checkout": "", "huespedes": 1, "estrellas_min": "", "precio_max": "", "calificacion_min": ""}
    filtros.update(filtros_extra)
    return templates.TemplateResponse(
        request, "buscar_hoteles.html", {"resultados": None, "ciudades": ciudades, "filtros": filtros, "usuario": usuario}
    )


@router.get("/buscar")
async def buscar(
    request: Request,
    ciudad: str | None = None,
    checkin: str | None = None,
    checkout: str | None = None,
    huespedes: int = 1,
    estrellas_min: float | None = None,
    precio_max: float | None = None,
    calificacion_min: float | None = None,
    usuario: dict | None = Depends(usuario_opcional),
):
    if not ciudad:
        return await _formulario_vacio(
            request, usuario, estrellas_min=estrellas_min or "", precio_max=precio_max or "", calificacion_min=calificacion_min or ""
        )

    await registrar_busqueda_reciente(
        usuario, "hotel",
        {"ciudad": ciudad, "checkin": checkin or "", "checkout": checkout or "", "huespedes": huespedes},
    )
    repo = HotelesRepository()
    hoteles = await repo.buscar_por_ciudad(ciudad)
    hoteles = [await _con_precio_desde(repo, h) for h in hoteles]
    hoteles = _filtrar(hoteles, estrellas_min, precio_max, calificacion_min)

    resultados = [
        HotelBusquedaOut(
            id=h["id"], nombre=h["nombre"], ciudad=h["ciudad"], estrellas=h.get("estrellas"),
            calificacion_promedio=h.get("calificacion_promedio"), cantidad_resenas=h.get("cantidad_resenas"),
            precio_desde=h.get("precio_desde"), imagen_principal=h.get("imagen_principal"),
        )
        for h in hoteles
    ]
    resultados.sort(key=lambda r: r.precio_desde if r.precio_desde is not None else float("inf"))

    ciudades = await repo.ciudades_disponibles()

    return templates.TemplateResponse(
        request,
        "buscar_hoteles.html",
        {
            "resultados": resultados,
            "ciudades": ciudades,
            "filtros": {
                "ciudad": ciudad, "checkin": checkin or "", "checkout": checkout or "", "huespedes": huespedes,
                "estrellas_min": estrellas_min or "", "precio_max": precio_max or "", "calificacion_min": calificacion_min or "",
            },
            "usuario": usuario,
        },
    )


@router.get("/{hotel_id}")
async def detalle(request: Request, hotel_id: str, usuario: dict | None = Depends(usuario_opcional)):
    repo = HotelesRepository()
    hotel = await repo.obtener_hotel(hotel_id)
    if hotel is None:
        return templates.TemplateResponse(request, "detalle_hotel.html", {"hotel": None, "usuario": usuario}, status_code=404)

    tarifas = await repo.tarifas_de_hotel(hotel_id)
    tarifas.sort(key=lambda t: t.get("precio_final") or 0)
    resenas = await repo.resenas_de_hotel(hotel_id)
    cargos_locales = await repo.cargos_locales_de_ciudad(hotel["ciudad"])

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
        },
    )
