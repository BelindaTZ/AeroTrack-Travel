"""
AeroTrack Travel — DAG: Actualizar tasas de cambio (RF-FAC-011, CU-O85)
===========================================================================
Qué hace: 1×/día, consulta ExchangeRate-API (RapidAPI) para la moneda base
configurada (`configuracion_sistema.tasas_cambio.moneda_base`, USD por
defecto) contra cada moneda destino configurada, y upsertea `tasas_cambio`
con la tasa vigente. Presentación de precio únicamente — el cobro real vía
Stripe sigue siempre en USD (facturacion-spec.md RF-FAC-011).

UI: http://localhost:8081 -> busca "aerotrack_travel_tasas_cambio"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from tasas_cambio_tasks import actualizar_tasas_cambio


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de tasas de cambio")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_tasas_cambio",
    description="RF-FAC-011/CU-O85: actualiza tasas_cambio 1x/día contra ExchangeRate-API (RapidAPI)",
    schedule="@daily",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    dagrun_timeout=timedelta(minutes=5),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "facturacion", "pocketbase-travel", "api-externa"],
)
def aerotrack_travel_tasas_cambio():
    @task(task_id="actualizar_tasas", execution_timeout=timedelta(minutes=2))
    def actualizar() -> int:
        return actualizar_tasas_cambio()

    actualizar()


dag_instance = aerotrack_travel_tasas_cambio()
