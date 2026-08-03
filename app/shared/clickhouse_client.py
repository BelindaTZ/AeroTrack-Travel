"""Cliente ClickHouse de solo lectura para la app (dashboards). La carga de
datos la hacen los DAGs `aerotrack_travel_etl_*` (ver dags/clickhouse_client.py)
— la app nunca inserta acá, solo consulta las tablas `agg_*` ya cargadas."""

from __future__ import annotations

import datetime

from clickhouse_driver import Client

from app.shared.config import get_settings


def _conectar() -> Client:
    settings = get_settings()
    return Client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_db,
    )


def _json_seguro(valor):
    """`date`/`datetime` de columnas ClickHouse (ej. `periodo`) no son
    serializables por `JSONResponse` — se normalizan acá una sola vez en
    vez de en cada service que arme un endpoint de dashboard."""
    if isinstance(valor, (datetime.date, datetime.datetime)):
        return valor.isoformat()
    return valor


def query_dicts(sql: str, params: dict | None = None) -> list[dict]:
    """Ejecuta `sql` y devuelve las filas como lista de dicts (nombre de
    columna -> valor), para serializar directo a JSON en los endpoints."""
    cliente = _conectar()
    filas, columnas = cliente.execute(sql, params or {}, with_column_types=True)
    nombres = [c[0] for c in columnas]
    return [{nombre: _json_seguro(valor) for nombre, valor in zip(nombres, fila)} for fila in filas]
