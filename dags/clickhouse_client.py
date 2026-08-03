"""
AeroTrack Travel — Cliente ClickHouse reutilizable para los DAGs ETL
=====================================================================
Helper compartido por los 5 DAGs `aerotrack_travel_etl_*`. Mismo patrón
de módulo flat que `pocketbase_client.py`/`minio_dims_reader.py` (import
directo, sin paquete) — así funciona en Airflow, que agrega `dags/` a
`sys.path` para parsear los DAGs.

`insertar_df` reemplaza filas por clave de ORDER BY porque todas las
tablas usan `ReplacingMergeTree()` — reinsertar el mismo período/tipo
producto en una corrida posterior no duplica, se deduplica en el próximo
merge (o con FINAL en las consultas, si hace falta antes de eso).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from clickhouse_driver import Client

import config


def conectar() -> Client:
    """Cliente nativo de ClickHouse contra la base `aerotrack_travel`."""
    return Client(
        host=config.CLICKHOUSE_HOST,
        port=config.CLICKHOUSE_PORT,
        user=config.CLICKHOUSE_USER,
        password=config.CLICKHOUSE_PASSWORD,
        database=config.CLICKHOUSE_DB,
    )


def ejecutar_query(sql: str, params: dict | None = None) -> list[tuple]:
    """Ejecuta una query arbitraria (DDL/SELECT) y devuelve las filas
    (lista vacía para DDL, que no devuelve resultset)."""
    cliente = conectar()
    return cliente.execute(sql, params or {})


def insertar_df(tabla: str, df: pd.DataFrame) -> int:
    """Inserta un DataFrame pandas en `tabla` (columnas del DataFrame deben
    calzar 1:1 en nombre y orden con las columnas reales de la tabla).
    Devuelve la cantidad de filas insertadas. No hace nada si `df` viene
    vacío (evita el INSERT de 0 filas, que `clickhouse-driver` acepta pero
    no aporta nada registrar en el log de la tarea)."""
    if df.empty:
        return 0
    cliente = conectar()
    columnas = ", ".join(df.columns)
    registros = df.to_dict("records")
    cliente.execute(f"INSERT INTO {tabla} ({columnas}) VALUES", registros)
    return len(registros)


def mover_parquet(nombre_archivo: str, origen: Path, destino: Path) -> Path:
    """Mueve `nombre_archivo` de la carpeta `origen` a `destino` del
    pipeline crudo/procesando/terminado. Crea `destino` si no existe
    (primera corrida). Devuelve la ruta final."""
    destino.mkdir(parents=True, exist_ok=True)
    ruta_origen = origen / nombre_archivo
    ruta_destino = destino / nombre_archivo
    shutil.move(str(ruta_origen), str(ruta_destino))
    return ruta_destino


def escribir_parquet(df: pd.DataFrame, nombre_archivo: str, carpeta: Path) -> Path:
    """Escribe `df` como Parquet en `carpeta/nombre_archivo`, creando la
    carpeta si hace falta (primera corrida de un DAG nuevo)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre_archivo
    df.to_parquet(ruta, index=False)
    return ruta
