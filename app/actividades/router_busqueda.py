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

from app.actividades.repositories.actividades_repo import ActividadesRepository
from app.actividades.schemas import ActividadBusquedaOut
from app.seguridad.services.session_service import usuario_opcional
from app.shared.busqueda_reciente import registrar_busqueda_reciente
from app.shared.templating import templates

router = APIRouter(prefix="/actividades")


def _filtrar(actividades: list[dict], categoria: str, precio_max: float | None, calificacion_min: float | None) -> list[dict]:
    resultado = actividades
    if categoria:
        resultado = [a for a in resultado if a.get("categoria") == categoria]
    if precio_max is not None:
        resultado = [a for a in resultado if a.get("precio_desde") is not None and a["precio_desde"] <= precio_max]
    if calificacion_min is not None:
        resultado = [a for a in resultado if (a.get("calificacion_promedio") or 0) >= calificacion_min]
    return resultado


async def _formulario_vacio(request: Request, usuario: dict | None, **filtros_extra) -> object:
    repo = ActividadesRepository()
    ciudades = await repo.ciudades_disponibles()
    filtros = {"ciudad": "", "categoria": "", "precio_max": "", "calificacion_min": ""}
    filtros.update(filtros_extra)
    return templates.TemplateResponse(
        request, "buscar_actividades.html", {"resultados": None, "ciudades": ciudades, "filtros": filtros, "usuario": usuario}
    )


@router.get("/buscar")
async def buscar(
    request: Request,
    ciudad: str | None = None,
    categoria: str = "",
    precio_max: float | None = None,
    calificacion_min: float | None = None,
    usuario: dict | None = Depends(usuario_opcional),
):
    if not ciudad:
        return await _formulario_vacio(
            request, usuario, categoria=categoria, precio_max=precio_max or "", calificacion_min=calificacion_min or ""
        )

    await registrar_busqueda_reciente(usuario, "actividad", {"ciudad": ciudad})
    repo = ActividadesRepository()
    actividades = await repo.buscar_por_ciudad(ciudad)

    categorias = sorted({a["categoria"] for a in actividades if a.get("categoria")})

    actividades = _filtrar(actividades, categoria, precio_max, calificacion_min)
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

    ciudades = await repo.ciudades_disponibles()

    return templates.TemplateResponse(
        request,
        "buscar_actividades.html",
        {
            "resultados": resultados,
            "ciudades": ciudades,
            "categorias": categorias,
            "filtros": {
                "ciudad": ciudad, "categoria": categoria,
                "precio_max": precio_max or "", "calificacion_min": calificacion_min or "",
            },
            "usuario": usuario,
        },
    )


@router.get("/{actividad_id}")
async def detalle(request: Request, actividad_id: str, fecha: date | None = None, usuario: dict | None = Depends(usuario_opcional)):
    repo = ActividadesRepository()
    actividad = await repo.obtener_actividad(actividad_id)
    if actividad is None:
        return templates.TemplateResponse(request, "detalle_actividad.html", {"actividad": None, "usuario": usuario}, status_code=404)

    resenas = await repo.resenas_de_actividad(actividad_id)
    horarios_todos = await repo.horarios_de_actividad(actividad_id)
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
