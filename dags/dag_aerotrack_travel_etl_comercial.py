"""
AeroTrack Travel — DAG: ETL comercial -> ClickHouse
======================================================
docs/aerotrack-travel-dashboards-spec.md sección 1 — Fase B.2. Alimenta
`agg_ingresos_por_producto_mes` y `agg_conversion_busqueda_reserva` desde
reservas/reserva_items/carrito_items/busquedas_recientes/pagos/facturas/
comisiones/reembolsos, vía los endpoints internos de solo lectura
(`app/shared/router_interno_analitica.py`) — ver
`aerotrack_travel_etl_comercial_tasks.py` para las decisiones de diseño
sobre atribución de comisiones/reembolsos y definición del funnel.

UI: http://localhost:8081 -> busca "aerotrack_travel_etl_comercial"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from aerotrack_travel_etl_comercial_tasks import cargar, extraer, transformar


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN aerotrack_travel_etl_comercial")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_etl_comercial",
    description="Carga agg_ingresos_por_producto_mes/agg_conversion_busqueda_reserva en ClickHouse",
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
    tags=["aerotrack-travel", "etl", "clickhouse", "comercial"],
)
def aerotrack_travel_etl_comercial():
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


dag_instance = aerotrack_travel_etl_comercial()
