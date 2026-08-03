"""RF-HOT-004 (gap real cerrado 2026-07-29) — disponibilidad real por
noche para búsqueda/detalle. Overlay del cupo vigente
(`app.shared.cupo_service`, MinIO) sobre el snapshot congelado en
PocketBase (`hoteles_disponibilidad`), mismo criterio que ya usan
vuelos/actividades/cruceros."""

from app.hoteles.repositories.catalogo_reader import CatalogoHotelesReader
from app.shared.cupo_service import cupos_vigentes
from app.shared.rango_fechas import fechas_rango


async def cupo_minimo_en_rango(hotel_tarifa_id: str, checkin: str, checkout: str) -> int | None:
    """Cupo real MÍNIMO entre todas las noches de `[checkin, checkout)` —
    la noche más floja del rango manda. `None` si el rango está vacío o si
    falta alguna noche (fuera de la ventana `disponibilidad_hoteles.
    dias_adelante` ya generada) — nunca se inventa disponibilidad."""
    fechas = fechas_rango(checkin, checkout)
    if not fechas:
        return None

    filas = await CatalogoHotelesReader().disponibilidad_de_tarifa(hotel_tarifa_id)
    por_fecha = {fila["fecha"][:10]: fila for fila in filas}
    vigentes = await cupos_vigentes("hoteles_disponibilidad")

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
