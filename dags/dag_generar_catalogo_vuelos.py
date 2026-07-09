"""
AeroTrack Travel — DAG: Generar catálogo de vuelos programables (CU-O30)
===========================================================================
Qué hace: cada día, asegura que exista un vuelo programado por cada ruta
curada (hubs reales, ver catalogo_vuelos_tasks.HUBS) para los próximos 7
días (ventana móvil), y marca como 'completado' cualquier vuelo cuya
llegada programada ya pasó (CU-O31, versión sin API externa).

    [generar_vuelos] >> [actualizar_estados]

Fuente de rutas: dim_ruta en aerotrack-travel-dims (solo lectura).
Escribe en: vuelos_catalogo y tarifas_vuelo, en pocketbase-travel.

UI: http://localhost:8081 -> busca "aerotrack_travel_catalogo_vuelos"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from catalogo_vuelos_tasks import actualizar_estados_vuelos, generar_vuelos_programables


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de catálogo de vuelos")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_catalogo_vuelos",
    description="CU-O30/O31: genera catálogo de vuelos programables (ventana móvil de 7 días) y actualiza estados vencidos",
    schedule="@daily",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=30),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "vuelos_catalogo", "pocketbase-travel"],
)
def aerotrack_travel_catalogo_vuelos():
    @task(task_id="generar_vuelos", execution_timeout=timedelta(minutes=15))
    def generar_vuelos() -> int:
        return generar_vuelos_programables()

    @task(task_id="actualizar_estados", execution_timeout=timedelta(minutes=10))
    def actualizar_estados(_creados: int) -> int:
        return actualizar_estados_vuelos()

    creados = generar_vuelos()
    actualizar_estados(creados)


dag_instance = aerotrack_travel_catalogo_vuelos()
