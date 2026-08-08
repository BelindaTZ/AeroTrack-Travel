"""
AeroTrack Travel — DAG: ETL dims BTS/FAA -> ClickHouse
=========================================================
docs/aerotrack-travel-dashboards-spec.md sección 1 — primer DAG del
pipeline de dashboards (Fase B.1). Patrón de 3 tareas extraer/transformar/
cargar sobre datos/E -> datos/T -> datos/L, igual que los demás
DAGs de este proyecto (ver `dag_publicar_catalogo_minio.py`).

Alimenta `agg_otp_aerolinea_mes`, `agg_causas_retraso_mes`,
`agg_otp_dia_semana` en ClickHouse (`aerotrack_travel`) a partir de
`fact_vuelo.parquet` + 5 dimensiones de `aerotrack-travel-dims` — ver
`aerotrack_travel_etl_dims_tasks.py` para el detalle de los joins (el
esquema real es en estrella, no columnas planas).

UI: http://localhost:8081 -> busca "aerotrack_travel_etl_dims"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from aerotrack_travel_etl_dims_tasks import cargar, extraer, transformar


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN aerotrack_travel_etl_dims")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_etl_dims",
    description="Carga agg_otp_aerolinea_mes/agg_causas_retraso_mes/agg_otp_dia_semana en ClickHouse desde fact_vuelo (BTS/FAA)",
    schedule="@hourly",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=1),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "etl", "clickhouse", "dims"],
)
def aerotrack_travel_etl_dims():
    @task(task_id="extraer", execution_timeout=timedelta(minutes=15))
    def _extraer() -> dict:
        return extraer()

    @task(task_id="transformar", execution_timeout=timedelta(minutes=20))
    def _transformar(extraido: dict) -> dict:
        return transformar(extraido)

    @task(task_id="cargar", execution_timeout=timedelta(minutes=15))
    def _cargar(transformado: dict) -> dict:
        return cargar(transformado)

    _cargar(_transformar(_extraer()))


dag_instance = aerotrack_travel_etl_dims()
