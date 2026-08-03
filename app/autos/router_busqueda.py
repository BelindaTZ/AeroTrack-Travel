"""RF-AUT-001,002,003 (CU-O61,O62,O63) — buscar autos disponibles por
ciudad/fechas, ver detalle y filtrar resultados (instantáneo, REG-J9)."""

from fastapi import APIRouter, Depends, Request

from app.autos.repositories.catalogo_reader import CatalogoAutosReader
from app.autos.schemas import AutoBusquedaOut
from app.autos.services.disponibilidad_service import cupo_minimo_en_rango
from app.seguridad.services.session_service import usuario_opcional
from app.shared.busqueda_reciente import registrar_busqueda_reciente
from app.shared.rango_fechas import fechas_rango
from app.shared.templating import templates

router = APIRouter(prefix="/autos")


def _parse_float(valor: str | None) -> float | None:
    """String, no `float` nativo de FastAPI: el form oculto de filtros
    siempre manda `precio_max` aunque esté vacío — con un tipo `float`
    nativo, FastAPI rechaza "" con 422 en vez de tratarlo como "sin valor"
    (mismo fix que en vuelos/hoteles `router_busqueda.py`)."""
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _filtrar(autos: list[dict], categoria: str, transmision: str, precio_max: float | None) -> list[dict]:
    resultado = autos
    if categoria:
        resultado = [a for a in resultado if a.get("categoria") == categoria]
    if transmision:
        resultado = [a for a in resultado if a.get("transmision") == transmision]
    if precio_max is not None:
        resultado = [a for a in resultado if a.get("precio_dia") is not None and a["precio_dia"] <= precio_max]
    return resultado


def _opciones_ciudades(ciudades: list[str]) -> list[dict]:
    return [{"valor": c, "principal": c, "secundario": None} for c in ciudades]


async def _formulario_vacio(request: Request, usuario: dict | None, **filtros_extra) -> object:
    catalogo = CatalogoAutosReader()
    ciudades = _opciones_ciudades(await catalogo.ciudades_disponibles())
    filtros = {"ciudad": "", "recogida": "", "devolucion": "", "categoria": "", "transmision": "", "precio_max": ""}
    filtros.update(filtros_extra)
    return templates.TemplateResponse(
        request, "buscar_autos.html", {"resultados": None, "ciudades": ciudades, "filtros": filtros, "usuario": usuario}
    )


@router.get("/buscar")
async def buscar(
    request: Request,
    ciudad: str | None = None,
    recogida: str | None = None,
    devolucion: str | None = None,
    categoria: str = "",
    transmision: str = "",
    precio_max: str | None = None,
    usuario: dict | None = Depends(usuario_opcional),
):
    precio_max_val = _parse_float(precio_max)
    if not ciudad:
        return await _formulario_vacio(request, usuario, categoria=categoria, transmision=transmision, precio_max=precio_max_val or "")

    await registrar_busqueda_reciente(
        usuario, "auto", {"ciudad": ciudad, "recogida": recogida or "", "devolucion": devolucion or ""}
    )
    catalogo = CatalogoAutosReader()
    autos = await catalogo.buscar_por_ciudad(ciudad)

    categorias = sorted({a["categoria"] for a in autos if a.get("categoria")})
    transmisiones = sorted({a["transmision"] for a in autos if a.get("transmision")})

    autos = _filtrar(autos, categoria, transmision, precio_max_val)

    dias = None
    if recogida and devolucion:
        # RF-AUT-004 (gap real cerrado 2026-07-29) — antes recogida/
        # devolución eran cosméticas: con fechas, solo se muestran autos con
        # cupo real para TODO el rango (nunca días parciales).
        dias = len(fechas_rango(recogida, devolucion))
        con_disponibilidad = []
        for a in autos:
            cupo = await cupo_minimo_en_rango(a["id"], recogida, devolucion)
            if cupo is not None and cupo >= 1:
                con_disponibilidad.append(a)
        autos = con_disponibilidad

    resultados = [
        AutoBusquedaOut(
            id=a["id"],
            modelo=a.get("modelo") or a.get("categoria") or "Vehículo",
            categoria=a.get("categoria") or "",
            transmision=a.get("transmision"),
            proveedor_agregador=a["proveedor_agregador"],
            ciudad_recogida=a["ciudad_recogida"],
            precio_dia=a["precio_dia"],
            moneda=a.get("moneda") or "USD",
            modalidad_pago_disponible=a.get("modalidad_pago_disponible"),
            dias=dias,
            precio_total=(a["precio_dia"] * dias) if dias else None,
        )
        for a in autos
    ]
    resultados.sort(key=lambda r: r.precio_dia)

    ciudades = _opciones_ciudades(await catalogo.ciudades_disponibles())

    return templates.TemplateResponse(
        request,
        "buscar_autos.html",
        {
            "resultados": resultados,
            "ciudades": ciudades,
            "categorias": categorias,
            "transmisiones": transmisiones,
            "filtros": {
                "ciudad": ciudad, "recogida": recogida or "", "devolucion": devolucion or "",
                "categoria": categoria, "transmision": transmision, "precio_max": precio_max_val or "",
            },
            "usuario": usuario,
        },
    )


@router.get("/{auto_id}")
async def detalle(
    request: Request,
    auto_id: str,
    recogida: str | None = None,
    devolucion: str | None = None,
    usuario: dict | None = Depends(usuario_opcional),
):
    catalogo = CatalogoAutosReader()
    auto = await catalogo.obtener_auto(auto_id)
    if auto is None:
        return templates.TemplateResponse(request, "detalle_auto.html", {"auto": None, "usuario": usuario}, status_code=404)

    dias = None
    cupo = None
    precio_total = None
    if recogida and devolucion:
        dias = len(fechas_rango(recogida, devolucion))
        cupo = await cupo_minimo_en_rango(auto_id, recogida, devolucion)
        precio_total = auto["precio_dia"] * dias

    return templates.TemplateResponse(
        request,
        "detalle_auto.html",
        {
            "auto": auto, "usuario": usuario,
            "filtros": {"recogida": recogida or "", "devolucion": devolucion or "", "dias": dias},
            "cupo_disponible": cupo, "precio_total": precio_total,
        },
    )
