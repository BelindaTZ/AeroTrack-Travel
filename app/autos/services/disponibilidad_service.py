"""RF-AUT-004 (gap real cerrado 2026-07-29) — disponibilidad real por día
para búsqueda/detalle. Overlay del cupo vigente (`app.shared.cupo_service`,
MinIO) sobre el snapshot congelado en PocketBase (`autos_disponibilidad`),
mismo criterio que ya usan vuelos/actividades/cruceros/hoteles."""

from app.autos.repositories.catalogo_reader import CatalogoAutosReader
from app.shared.cupo_service import cupos_vigentes
from app.shared.rango_fechas import fechas_rango


async def cupo_minimo_en_rango(auto_id: str, recogida: str, devolucion: str) -> int | None:
    """Cupo real MÍNIMO entre todos los días de `[recogida, devolucion)` —
    el día más flojo del rango manda. `None` si el rango está vacío o si
    falta algún día (fuera de la ventana `disponibilidad_autos.
    dias_adelante` ya generada) — nunca se inventa disponibilidad."""
    fechas = fechas_rango(recogida, devolucion)
    if not fechas:
        return None

    filas = await CatalogoAutosReader().disponibilidad_de_auto(auto_id)
    por_fecha = {fila["fecha"][:10]: fila for fila in filas}
    vigentes = await cupos_vigentes("autos_disponibilidad")

    minimo = None
    for fecha in fechas:
        fila = por_fecha.get(fecha)
        if fila is None:
            return None
        cupo = vigentes.get(fila["id"], fila.get("cupos_disponibles"))
        if cupo is None:
            continue
        cupo = int(cupo)
        minimo = cupo if minimo is None else min(minimo, cupo)
    return minimo
