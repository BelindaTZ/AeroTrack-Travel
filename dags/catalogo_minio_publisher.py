"""
AeroTrack Travel — Publica colecciones STAGING de pocketbase-travel como
NDJSON en MinIO (`aerotrack-travel-catalog`), para que la app lea el
catálogo de búsqueda desde ahí en vez de PocketBase directo.

Cada colección STAGING se refresca completa (reemplazo total del objeto,
no append) — son catálogos de producto que se regeneran a diario desde las
APIs externas, no un log incremental. Ver plan de migración,
PASO 4/5 (STAGING -> catálogo NDJSON).
"""

from __future__ import annotations

import io
import json

from minio import Minio

import config
import pocketbase_client


def _client() -> Minio:
    return Minio(config.MINIO_ENDPOINT, access_key=config.MINIO_ACCESS, secret_key=config.MINIO_SECRET, secure=False)


def _asegurar_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def publicar_coleccion_ndjson(coleccion: str) -> int:
    """Lee toda la colección de pocketbase-travel y la vuelca como NDJSON
    en `catalogo/{coleccion}.ndjson`. Devuelve la cantidad de registros."""
    registros = pocketbase_client.list_all(coleccion)
    cuerpo = b"\n".join(json.dumps(r, ensure_ascii=False).encode("utf-8") for r in registros)

    client = _client()
    _asegurar_bucket(client, config.MINIO_BUCKET_TRAVEL_CATALOG)
    client.put_object(
        config.MINIO_BUCKET_TRAVEL_CATALOG,
        f"catalogo/{coleccion}.ndjson",
        io.BytesIO(cuerpo),
        length=len(cuerpo),
        content_type="application/x-ndjson",
    )
    return len(registros)


def publicar_grupo(colecciones: list[str]) -> dict[str, int]:
    """Publica varias colecciones de un mismo dominio (ej. las 3 de hoteles)
    y devuelve cuántos registros se escribieron por colección."""
    return {c: publicar_coleccion_ndjson(c) for c in colecciones}
