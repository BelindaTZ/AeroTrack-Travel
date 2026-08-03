"""
AeroTrack Travel — DAG: ETL clientes -> ClickHouse
=====================================================
docs/aerotrack-travel-dashboards-spec.md sección 1 — Fase B.4. Alimenta
`agg_segmentos_pasajero` y `agg_alertas_conversion` desde pasajeros/
reservas/reserva_items/alertas_precio (vía `/internal/analitica`) +
catálogos de producto (PocketBase STAGING, lectura directa, para resolver
`destino_frecuente`). Ver `aerotrack_travel_etl_clientes_tasks.py` para
las decisiones de diseño.

UI: http://localhost:8081 -> busca "aerotrack_travel_etl_clientes"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from aerotrack_travel_etl_clientes_tasks import cargar, extraer, transformar


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN aerotrack_travel_etl_clientes")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_etl_clientes",
    description="Carga agg_segmentos_pasajero/agg_alertas_conversion en ClickHouse",
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
    tags=["aerotrack-travel", "etl", "clickhouse", "clientes"],
)
def aerotrack_travel_etl_clientes():
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


dag_instance = aerotrack_travel_etl_clientes()
