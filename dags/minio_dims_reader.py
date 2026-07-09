"""
AeroTrack Travel — Lectura de solo lectura del modelo dimensional heredado
============================================================================
Principio A2 de la constitución: cualquier módulo que consulte el modelo
dimensional heredado (aquí: aerotrack-travel-dims) lo hace exclusivamente
en modo lectura. Este módulo NUNCA escribe a ese bucket.
"""

from __future__ import annotations

import io

import pandas as pd
import pyarrow.parquet as pq
from minio import Minio

import config


def _client() -> Minio:
    return Minio(config.MINIO_ENDPOINT, access_key=config.MINIO_ACCESS, secret_key=config.MINIO_SECRET, secure=False)


def read_parquet(nombre: str, columnas: list[str] | None = None) -> pd.DataFrame:
    """Lee un objeto Parquet de aerotrack-travel-dims directo a DataFrame,
    sin descargar a disco (el bucket es pequeño, ~47MiB en total)."""
    client = _client()
    resp = client.get_object(config.MINIO_BUCKET_TRAVEL_DIMS, f"{nombre}.parquet")
    try:
        buf = io.BytesIO(resp.read())
    finally:
        resp.close()
    pf = pq.ParquetFile(buf)
    disponibles = [c for c in (columnas or pf.schema_arrow.names) if c in pf.schema_arrow.names]
    return pf.read(columns=disponibles).to_pandas()
