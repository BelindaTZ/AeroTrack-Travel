"""RF-ACT-001,002,003,007,009 (CU-O65,O66,O67,O68,O70) — buscar
actividades, ver detalle con reseñas e inclusiones curadas, filtrar
(instantáneo, REG-J9) y ver horarios sintéticos disponibles.

RF-ACT-008 (CU-O69, seleccionar horario + participantes) se resuelve
posteando directo a `/carrito/agregar` (Carrito) con
`precio_snapshot = horario.precio * participantes` — no hay
`router_seleccion.py` propio, mismo criterio de reutilización que Autos.
**Caveat documentado** (`errores-conocidos.md`): la revalidación de Carrito
(RN-CAR-001) compara ese total contra `actividades_horarios.precio`
(precio UNITARIO vigente) — con participantes>1 puede mostrar un "cambio
de precio" que en realidad es solo la multiplicación, no una tarifa
distinta."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from app.actividades.repositories.catalogo_reader import CatalogoActividadesReader
from app.actividades.schemas import ActividadBusquedaOut
from app.seguridad.services.session_service import usuario_opcional
from app.shared.busqueda_reciente import registrar_busqueda_reciente
from app.shared.cupo_service import cupos_vigentes
from app.shared.templating import templates

router = APIRouter(prefix="/actividades")


def _parse_float(valor: str | None) -> float | None:
    """String, no `float` nativo de FastAPI: el form oculto de filtros
    siempre manda `precio_max`/`calificacion_min` aunque estén vacíos — con
    un tipo `float` nativo, FastAPI rechaza "" con 422 en vez de tratarlo
    como "sin valor" (mismo fix que en vuelos/hoteles/autos)."""
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _filtrar(actividades: list[dict], categoria: str, precio_max: float | None, calificacion_min: float | None) -> list[dict]:
    resultado = actividades
    if categoria:
        resultado = [a for a in resultado if a.get("categoria") == categoria]
    if precio_max is not None:
        resultado = [a for a in resultado if a.get("precio_desde") is not None and a["precio_desde"] <= precio_max]
    if calificacion_min is not None:
        resultado = [a for a in resultado if (a.get("calificacion_promedio") or 0) >= calificacion_min]
    return resultado


def _opciones_ciudades(ciudades: list[dict]) -> list[dict]:
    return [{"valor": c["ciudad"], "principal": c["ciudad"], "secundario": c["pais"] or None} for c in ciudades]


async def _tiene_horario_en_rango(
    catalogo: CatalogoActividadesReader, actividad_id: str, desde: str | None, hasta: str | None, cupos_reales: dict
) -> bool:
    """RF-ACT — a diferencia de hoteles/autos (rango de noches/días que
    hay que cubrir ENTERO), una actividad se reserva para UN horario
    puntual: basta con que exista al menos uno dentro de `[desde, hasta]`
    (ambos inclusive, cualquiera de los dos opcional) con cupo real > 0."""
    horarios = await catalogo.horarios_de_actividad(actividad_id)
    for h in horarios:
        fecha = h["fecha"][:10]
        if desde and fecha < desde:
            continue
        if hasta and fecha > hasta:
            continue
        cupo = cupos_reales.get(h["id"], h.get("cupos_disponibles"))
        if cupo is not None and int(cupo) > 0:
            return True
    return False


async def _formulario_vacio(request: Request, usuario: dict | None, **filtros_extra) -> object:
    catalogo = CatalogoActividadesReader()
    ciudades = _opciones_ciudades(await catalogo.ciudades_disponibles())
    filtros = {"ciudad": "", "categoria": "", "precio_max": "", "calificacion_min": "", "desde": "", "hasta": ""}
    filtros.update(filtros_extra)
    return templates.TemplateResponse(
        request, "buscar_actividades.html", {"resultados": None, "ciudades": ciudades, "filtros": filtros, "usuario": usuario}
    )


@router.get("/buscar")
async def buscar(
    request: Request,
    ciudad: str | None = None,
    categoria: str = "",
    precio_max: str | None = None,
    calificacion_min: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    usuario: dict | None = Depends(usuario_opcional),
):
    precio_max_val = _parse_float(precio_max)
    calificacion_min_val = _parse_float(calificacion_min)
    if not ciudad:
        return await _formulario_vacio(
            request, usuario, categoria=categoria, precio_max=precio_max_val or "", calificacion_min=calificacion_min_val or "",
            desde=desde.isoformat() if desde else "", hasta=hasta.isoformat() if hasta else "",
        )

    await registrar_busqueda_reciente(usuario, "actividad", {"ciudad": ciudad})
    catalogo = CatalogoActividadesReader()
    actividades = await catalogo.buscar_por_ciudad(ciudad)

    categorias = sorted({a["categoria"] for a in actividades if a.get("categoria")})

    if desde or hasta:
        # Nunca se fabrica disponibilidad: solo quedan las actividades con
        # al menos un horario real con cupo dentro del rango pedido, mismo
        # criterio "honesto" que hoteles/autos (RF-HOT-004/RF-AUT-004).
        desde_iso = desde.isoformat() if desde else None
        hasta_iso = hasta.isoformat() if hasta else None
        cupos_reales = await cupos_vigentes("actividades_horarios")
        actividades = [
            a for a in actividades
            if await _tiene_horario_en_rango(catalogo, a["id"], desde_iso, hasta_iso, cupos_reales)
        ]

    actividades = _filtrar(actividades, categoria, precio_max_val, calificacion_min_val)
    resultados = [
        ActividadBusquedaOut(
            id=a["id"], nombre=a["nombre"], ciudad=a["ciudad"], categoria=a.get("categoria"),
            calificacion_promedio=a.get("calificacion_promedio"), cantidad_resenas=a.get("cantidad_resenas"),
            precio_desde=a.get("precio_desde"), moneda=a.get("moneda") or "USD",
            imagen_principal=a.get("imagen_principal"),
        )
        for a in actividades
    ]
    resultados.sort(key=lambda r: r.precio_desde if r.precio_desde is not None else 0)

    ciudades = _opciones_ciudades(await catalogo.ciudades_disponibles())

    return templates.TemplateResponse(
        request,
        "buscar_actividades.html",
        {
            "resultados": resultados,
            "ciudades": ciudades,
            "categorias": categorias,
            "filtros": {
                "ciudad": ciudad, "categoria": categoria,
                "precio_max": precio_max_val or "", "calificacion_min": calificacion_min_val or "",
                "desde": desde.isoformat() if desde else "", "hasta": hasta.isoformat() if hasta else "",
            },
            "usuario": usuario,
        },
    )


@router.get("/{actividad_id}")
async def detalle(request: Request, actividad_id: str, fecha: date | None = None, usuario: dict | None = Depends(usuario_opcional)):
    catalogo = CatalogoActividadesReader()
    actividad = await catalogo.obtener_actividad(actividad_id)
    if actividad is None:
        return templates.TemplateResponse(request, "detalle_actividad.html", {"actividad": None, "usuario": usuario}, status_code=404)

    resenas = await catalogo.resenas_de_actividad(actividad_id)
    horarios_todos = await catalogo.horarios_de_actividad(actividad_id)
    # `actividades_horarios.cupos_disponibles` queda congelado en
    # PocketBase desde que el cupo real se decrementa en MinIO — overlay
    # con el valor vigente sin mutar los dicts cacheados del catálogo.
    cupos_reales = await cupos_vigentes("actividades_horarios")
    horarios_todos = [
        {**h, "cupos_disponibles": cupos_reales.get(h["id"], h.get("cupos_disponibles"))} for h in horarios_todos
    ]
    fechas_disponibles = sorted({h["fecha"][:10] for h in horarios_todos})

    horarios = horarios_todos
    if fecha:
        horarios = [h for h in horarios_todos if h["fecha"][:10] == fecha.isoformat()]

    return templates.TemplateResponse(
        request,
        "detalle_actividad.html",
        {
            "actividad": actividad,
            "resenas": resenas,
            "horarios": horarios,
            "fechas_disponibles": fechas_disponibles,
            "fecha_filtro": fecha.isoformat() if fecha else "",
            "usuario": usuario,
        },
    )
