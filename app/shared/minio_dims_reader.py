"""Lector de solo lectura del modelo dimensional heredado (REG-A1/A2).

Mecánica genérica sobre Parquet en MinIO (`aerotrack-travel-dims`) — sin
`pandas`, usa `pyarrow` directo porque solo se necesitan lecturas puntuales
(resolver un código a un nombre legible), no análisis tabular. Sin ningún
método de escritura en su interfaz: ningún módulo puede crear, modificar o
eliminar nada en esta capa a través de este cliente.

Nota de despliegue: este archivo es independiente de `dags/minio_dims_reader.py`
(mismo propósito, pero para el contenedor `app-travel`, que no incluye `dags/`
en su build — ver `Dockerfile`). No se importan entre sí.
"""

import asyncio
import io

import pyarrow.parquet as pq
from minio import Minio

from app.shared.config import get_settings


def _client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access,
        secret_key=settings.minio_secret,
        secure=False,
    )


def _leer_parquet_sync(nombre: str, columnas: list[str] | None = None) -> list[dict]:
    settings = get_settings()
    client = _client()
    resp = client.get_object(settings.minio_bucket_travel_dims, f"{nombre}.parquet")
    try:
        buf = io.BytesIO(resp.read())
    finally:
        resp.close()
    tabla = pq.read_table(buf, columns=columnas)
    return tabla.to_pylist()


async def leer_parquet(nombre: str, columnas: list[str] | None = None) -> list[dict]:
    """Lee un objeto Parquet de `aerotrack-travel-dims` como lista de dicts.

    `minio`/`pyarrow` son librerías síncronas — se ejecutan en un hilo aparte
    (`asyncio.to_thread`) para no bloquear el event loop de FastAPI.
    """
    return await asyncio.to_thread(_leer_parquet_sync, nombre, columnas)
