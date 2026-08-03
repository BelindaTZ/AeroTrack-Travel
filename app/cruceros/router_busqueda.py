"""RF-CRU-001,002,003,004 (CU-O71,O72,O73,O74) — buscar cruceros por
destino/duración, ver itinerario, información del barco y comparar fechas
de zarpe del mismo barco.

RF-CRU-007 (CU-O75, seleccionar camarote) se resuelve posteando directo a
`/carrito/agregar` (Carrito), mismo criterio de reutilización que Autos —
no hay `router_seleccion.py` propio."""

from datetime import date

from fastapi import APIRouter, Depends, Request

from app.cruceros.repositories.catalogo_reader import CatalogoCrucerosReader
from app.cruceros.repositories.cruceros_repo import CrucerosRepository
from app.cruceros.schemas import CruceroBusquedaOut
from app.seguridad.services.session_service import usuario_opcional
from app.shared.busqueda_reciente import registrar_busqueda_reciente
from app.shared.cupo_service import cupos_vigentes
from app.shared.google_apis.maps_embed import url_mapa_ruta
from app.shared.templating import templates

router = APIRouter(prefix="/cruceros")


def _nombre_puerto(puerto) -> str:
    """`itinerario_puertos` real (Cruise Pricing API) es una lista de
    `{"day": N, "port": "Seattle, Washington"}` — confirmado en vivo, no
    una lista plana de strings. Se acepta también string plano por si
    algún registro viejo/de prueba lo trae así."""
    if isinstance(puerto, dict):
        return str(puerto.get("port") or "")
    return str(puerto)


async def _armar_resultado(catalogo: CatalogoCrucerosReader, crucero: dict) -> CruceroBusquedaOut | None:
    naviera = await catalogo.obtener_naviera(crucero["naviera_id"])
    barco = await catalogo.obtener_barco(crucero["barco_id"])
    if naviera is None or barco is None:
        return None
    return CruceroBusquedaOut(
        id=crucero["id"], naviera_nombre=naviera["nombre"], barco_nombre=barco["nombre"],
        fecha_zarpe=crucero["fecha_zarpe"][:10], duracion_dias=crucero.get("duracion_dias"),
        precio_base=crucero["precio_base"], moneda=crucero.get("moneda") or "USD",
        puertos=[_nombre_puerto(p) for p in (crucero.get("itinerario_puertos") or [])],
    )


def _parse_float(valor: str | None) -> float | None:
    """String, no `float` nativo de FastAPI: el form oculto de filtros
    siempre manda estos campos aunque estén vacíos — con un tipo `float`
    nativo, FastAPI rechaza "" con 422 en vez de tratarlo como "sin valor"
    (mismo fix que en vuelos/hoteles/autos/actividades)."""
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _filtrar(
    cruceros: list[dict], destino: str, duracion_min: float | None, duracion_max: float | None, precio_max: float | None,
    desde: str | None = None, hasta: str | None = None,
) -> list[dict]:
    resultado = cruceros
    if destino:
        termino = destino.lower()
        resultado = [
            c for c in resultado
            if any(termino in _nombre_puerto(p).lower() for p in (c.get("itinerario_puertos") or []))
        ]
    if duracion_min is not None:
        resultado = [c for c in resultado if (c.get("duracion_dias") or 0) >= duracion_min]
    if duracion_max is not None:
        resultado = [c for c in resultado if (c.get("duracion_dias") or 0) <= duracion_max]
    if precio_max is not None:
        resultado = [c for c in resultado if c.get("precio_base") is not None and c["precio_base"] <= precio_max]
    if desde:
        # `cruceros_catalogo` es una fila POR ZARPE real (Cruise Pricing
        # API) — a diferencia de hoteles/actividades no hace falta ningún
        # overlay de cupo por fecha, `fecha_zarpe` ya es la fecha real.
        resultado = [c for c in resultado if (c.get("fecha_zarpe") or "")[:10] >= desde]
    if hasta:
        resultado = [c for c in resultado if (c.get("fecha_zarpe") or "")[:10] <= hasta]
    return resultado


def _opciones_puertos(puertos: list[str]) -> list[dict]:
    return [{"valor": p, "principal": p, "secundario": None} for p in puertos]


@router.get("/buscar")
async def buscar(
    request: Request,
    destino: str | None = None,
    duracion_min: str | None = None,
    duracion_max: str | None = None,
    precio_max: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    usuario: dict | None = Depends(usuario_opcional),
):
    duracion_min_val = _parse_float(duracion_min)
    duracion_max_val = _parse_float(duracion_max)
    precio_max_val = _parse_float(precio_max)
    desde_iso = desde.isoformat() if desde else ""
    hasta_iso = hasta.isoformat() if hasta else ""

    catalogo = CatalogoCrucerosReader()
    puertos = _opciones_puertos(await catalogo.puertos_disponibles())

    if not destino:
        return templates.TemplateResponse(
            request, "buscar_cruceros.html",
            {
                "resultados": None, "puertos": puertos,
                "filtros": {
                    "destino": "", "duracion_min": "", "duracion_max": "", "precio_max": "",
                    "desde": desde_iso, "hasta": hasta_iso,
                },
                "usuario": usuario,
            },
        )

    await registrar_busqueda_reciente(usuario, "crucero", {"destino": destino})
    cruceros = _filtrar(
        await catalogo.listar_cruceros(), destino, duracion_min_val, duracion_max_val, precio_max_val, desde_iso, hasta_iso
    )
    resultados = [r for c in cruceros if (r := await _armar_resultado(catalogo, c)) is not None]
    resultados.sort(key=lambda r: r.precio_base)

    return templates.TemplateResponse(
        request,
        "buscar_cruceros.html",
        {
            "resultados": resultados,
            "puertos": puertos,
            "filtros": {
                "destino": destino, "duracion_min": duracion_min_val or "", "duracion_max": duracion_max_val or "",
                "precio_max": precio_max_val or "", "desde": desde_iso, "hasta": hasta_iso,
            },
            "usuario": usuario,
        },
    )


@router.get("/barco/{barco_id}/fechas")
async def comparar_fechas(request: Request, barco_id: str, usuario: dict | None = Depends(usuario_opcional)):
    """RF-CRU-004 (CU-O73) — mismo barco, distintas fechas de zarpe, precio
    por tipo de camarote de cada una lado a lado."""
    catalogo = CatalogoCrucerosReader()
    barco = await catalogo.obtener_barco(barco_id)
    if barco is None:
        return templates.TemplateResponse(request, "comparar_fechas.html", {"barco": None, "usuario": usuario}, status_code=404)

    naviera = await catalogo.obtener_naviera(barco["naviera_id"])
    cruceros = await catalogo.cruceros_de_barco(barco_id)
    salidas = []
    for c in cruceros:
        camarotes = await catalogo.camarotes_de_crucero(c["id"])
        salidas.append({"crucero": c, "camarotes": camarotes})

    return templates.TemplateResponse(
        request, "comparar_fechas.html", {"barco": barco, "naviera": naviera, "salidas": salidas, "usuario": usuario}
    )


@router.get("/{crucero_id}")
async def detalle(request: Request, crucero_id: str, usuario: dict | None = Depends(usuario_opcional)):
    """RF-CRU-002,003,007 (CU-O72,O74,O75) — itinerario, barco y selección
    de camarote en una sola pantalla."""
    repo = CrucerosRepository()  # solo para lectura CONFIG (maps_embed_api_key)
    catalogo = CatalogoCrucerosReader()
    crucero = await catalogo.obtener_crucero(crucero_id)
    if crucero is None:
        return templates.TemplateResponse(request, "detalle_crucero.html", {"crucero": None, "usuario": usuario}, status_code=404)

    naviera = await catalogo.obtener_naviera(crucero["naviera_id"])
    barco = await catalogo.obtener_barco(crucero["barco_id"])
    camarotes = await catalogo.camarotes_de_crucero(crucero_id)
    # `cruceros_camarotes_tarifa.cupos_disponibles` queda congelado en
    # PocketBase desde que el cupo real se decrementa en MinIO — overlay
    # con el valor vigente sin mutar los dicts cacheados del catálogo.
    cupos_reales = await cupos_vigentes("cruceros_camarotes_tarifa")
    camarotes = [
        {**c, "cupos_disponibles": cupos_reales.get(c["id"], c.get("cupos_disponibles"))} for c in camarotes
    ]

    itinerario = [
        {"day": p.get("day") if isinstance(p, dict) else None, "port": _nombre_puerto(p)}
        for p in (crucero.get("itinerario_puertos") or [])
    ]

    mapa_ruta_url = None
    api_key = await repo.config("google_apis.maps_embed_api_key")
    if api_key:
        mapa_ruta_url = url_mapa_ruta([p["port"] for p in itinerario], api_key)

    return templates.TemplateResponse(
        request,
        "detalle_crucero.html",
        {
            "crucero": crucero, "naviera": naviera, "barco": barco, "camarotes": camarotes,
            "itinerario": itinerario, "mapa_ruta_url": mapa_ruta_url, "usuario": usuario,
        },
    )
