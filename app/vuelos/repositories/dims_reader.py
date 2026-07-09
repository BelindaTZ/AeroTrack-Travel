"""RNF-VUE-001 — resolver origen/destino a nombre legible (ciudad, código).

Usa `app/shared/minio_dims_reader.py` (mecánica genérica de lectura Parquet)
sobre `dim_aeropuerto`. El modelo heredado es estático durante la vida del
proceso, así que se cachea en memoria tras la primera lectura.
"""

from app.shared.minio_dims_reader import leer_parquet

_cache: dict[str, str] | None = None


async def _cargar_cache() -> dict[str, str]:
    global _cache
    if _cache is None:
        filas = await leer_parquet("dim_aeropuerto", ["AirportCode", "CityName"])
        _cache = {fila["AirportCode"]: fila["CityName"] for fila in filas}
    return _cache


async def resolver_aeropuerto(codigo: str) -> str:
    cache = await _cargar_cache()
    ciudad = cache.get(codigo)
    return f"{ciudad} ({codigo})" if ciudad else codigo
