"""Lector de solo lectura del catálogo NDJSON publicado por el ETL de
staging (`dags/dag_publicar_catalogo_minio.py`) en `aerotrack-travel-catalog`.

PocketBase sigue siendo el origen real de las colecciones STAGING — los
DAGs de generación de catálogo y los endpoints de enriquecimiento en
`router_interno.py` de cada módulo siguen escribiendo ahí sin cambios. Este
lector solo consume el snapshot NDJSON que el ETL publica a diario, para
las rutas de búsqueda/detalle (ver plan de migración PASO 3/5).

Cache en memoria con TTL corto: el catálogo se refresca a diario, no hace
falta bajar el NDJSON completo en cada búsqueda de un usuario.
"""

from __future__ import annotations

import asyncio
import io
import json
import time

from minio import Minio

from app.shared.config import get_settings

_TTL_SEGUNDOS = 300
_cache: dict[str, tuple[float, list[dict]]] = {}
_lock = asyncio.Lock()


def _client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access,
        secret_key=settings.minio_secret,
        secure=False,
    )


def _leer_ndjson_sync(coleccion: str) -> list[dict]:
    settings = get_settings()
    client = _client()
    resp = client.get_object(settings.minio_bucket_travel_catalog, f"catalogo/{coleccion}.ndjson")
    try:
        cuerpo = resp.read()
    finally:
        resp.close()
    if not cuerpo:
        return []
    return [json.loads(linea) for linea in cuerpo.split(b"\n") if linea]


def _fecha_publicacion_sync(coleccion: str) -> str | None:
    settings = get_settings()
    client = _client()
    stat = client.stat_object(settings.minio_bucket_travel_catalog, f"catalogo/{coleccion}.ndjson")
    return stat.last_modified.strftime("%Y-%m-%d %H:%M:%S UTC") if stat.last_modified else None


async def fecha_publicacion(coleccion: str) -> str | None:
    """IS-07 (auditoría de informes simples, sesión 2026-08-01) — fecha de
    la última vez que el DAG publicó este NDJSON, no de cada registro
    individual. Es lo único que permite ver, desde el backoffice, si el
    snapshot que la búsqueda pública realmente usa está desfasado respecto
    a PocketBase (hasta 24h de desfase por diseño, ver auditoría IS-07)."""
    try:
        return await asyncio.to_thread(_fecha_publicacion_sync, coleccion)
    except Exception:
        return None


async def leer_coleccion(coleccion: str) -> list[dict]:
    """Lee una colección del catálogo NDJSON, cacheada en memoria por
    `_TTL_SEGUNDOS` para no bajar el archivo completo en cada búsqueda."""
    cacheado = _cache.get(coleccion)
    if cacheado and (time.monotonic() - cacheado[0]) < _TTL_SEGUNDOS:
        return cacheado[1]

    async with _lock:
        cacheado = _cache.get(coleccion)
        if cacheado and (time.monotonic() - cacheado[0]) < _TTL_SEGUNDOS:
            return cacheado[1]
        datos = await asyncio.to_thread(_leer_ndjson_sync, coleccion)
        _cache[coleccion] = (time.monotonic(), datos)
        return datos


def _escribir_ndjson_sync(coleccion: str, registros: list[dict]) -> None:
    settings = get_settings()
    cuerpo = "\n".join(json.dumps(r, ensure_ascii=False) for r in registros).encode("utf-8")
    client = _client()
    client.put_object(
        settings.minio_bucket_travel_catalog,
        f"catalogo/{coleccion}.ndjson",
        io.BytesIO(cuerpo),
        length=len(cuerpo),
        content_type="application/x-ndjson",
    )


async def publicar_y_refrescar(coleccion: str) -> list[dict]:
    """Vuelve a publicar `coleccion` completa desde PocketBase a MinIO
    (mismo formato que `dags/catalogo_minio_publisher.py`) y refresca el
    cache en memoria con el resultado.

    En producción esto lo hace el DAG diario (`dag_publicar_catalogo_minio`).
    Se expone acá para que las pruebas puedan sincronizar el catálogo justo
    después de sembrar datos de prueba en PocketBase, sin depender de que
    el DAG ya haya corrido — el catálogo es, por diseño, una copia con
    latencia de PocketBase, y esta es la manera explícita de adelantar esa
    latencia en vez de asumir consistencia inmediata.
    """
    from app.shared.pocketbase_client import get_pocketbase_client

    pb = get_pocketbase_client()
    registros: list[dict] = []
    pagina = 1
    while True:
        resultado = await pb.list_records(coleccion, {"page": pagina, "perPage": 200})
        registros.extend(resultado["items"])
        if pagina >= resultado.get("totalPages", 1):
            break
        pagina += 1

    await asyncio.to_thread(_escribir_ndjson_sync, coleccion, registros)
    _cache[coleccion] = (time.monotonic(), registros)
    return registros
