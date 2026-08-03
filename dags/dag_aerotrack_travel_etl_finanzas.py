"""
AeroTrack Travel — DAG: ETL finanzas -> ClickHouse
=====================================================
docs/aerotrack-travel-dashboards-spec.md sección 1 — Fase B.5 (último DAG
de la fase). Alimenta `agg_paquetes_margen_mes` desde reservas/
reserva_items (vía `/internal/analitica`). Ver
`aerotrack_travel_etl_finanzas_tasks.py` para el gap real de datos sobre
`costo_componentes` (no existe ningún campo de costo en el esquema hoy).

UI: http://localhost:8081 -> busca "aerotrack_travel_etl_finanzas"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from aerotrack_travel_etl_finanzas_tasks import cargar, extraer, transformar


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN aerotrack_travel_etl_finanzas")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_etl_finanzas",
    description="Carga agg_paquetes_margen_mes en ClickHouse",
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
    tags=["aerotrack-travel", "etl", "clickhouse", "finanzas"],
)
def aerotrack_travel_etl_finanzas():
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


dag_instance = aerotrack_travel_etl_finanzas()
