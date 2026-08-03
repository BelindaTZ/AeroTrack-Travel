"""
AeroTrack Travel — DAG: ETL operaciones -> ClickHouse
========================================================
docs/aerotrack-travel-dashboards-spec.md sección 1 — Fase B.3. Alimenta
`agg_disrupciones_aerolinea_ruta` y `agg_satisfaccion_soporte` desde
disrupciones/notificaciones/casos_escalados/mensajes_ia (vía
`/internal/analitica`) + vuelos_catalogo/aerolineas (PocketBase STAGING,
lectura directa). Ver `aerotrack_travel_etl_operaciones_tasks.py` para los
gaps de datos/esquema encontrados (documentados en el docstring de ese
archivo).

UI: http://localhost:8081 -> busca "aerotrack_travel_etl_operaciones"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from aerotrack_travel_etl_operaciones_tasks import cargar, extraer, transformar


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN aerotrack_travel_etl_operaciones")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_etl_operaciones",
    description="Carga agg_disrupciones_aerolinea_ruta/agg_satisfaccion_soporte en ClickHouse",
    schedule="@hourly",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=30),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "etl", "clickhouse", "operaciones"],
)
def aerotrack_travel_etl_operaciones():
    @task(task_id="extraer", execution_timeout=timedelta(minutes=10))
    def _extraer() -> dict:
        return extraer()

    @task(task_id="transformar", execution_timeout=timedelta(minutes=10))
    def _transformar(extraido: dict) -> dict:
        return transformar(extraido)

    @task(task_id="cargar", execution_timeout=timedelta(minutes=10))
    def _cargar(transformado: dict) -> dict:
        return cargar(transformado)

    _cargar(_transformar(_extraer()))


dag_instance = aerotrack_travel_etl_operaciones()
