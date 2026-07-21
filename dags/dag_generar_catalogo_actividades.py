"""AeroTrack Travel — DAG: Generar catálogo de actividades (RF-ACT-004/005/006, CU-O120/O121)
===========================================================================
Qué hace: dispara `POST /internal/actividades/generar-catalogo` en
`app-travel`. Toda la lógica real (Travel Advisor + disponibilidad
sintética en el mismo ciclo) vive en
`app/actividades/services/catalogo_service.py` — este DAG es un
disparador delgado, mismo patrón que Hoteles/Autos.

UI: http://localhost:8081 -> busca "aerotrack_travel_catalogo_actividades"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de catálogo de actividades")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_catalogo_actividades",
    description="RF-ACT-004/005/006, CU-O120/O121: genera actividades_catalogo/resenas/horarios vía Travel Advisor + regla sintética",
    schedule="@daily",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    dagrun_timeout=timedelta(minutes=10),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "actividades", "app-travel", "api-externa"],
)
def aerotrack_travel_catalogo_actividades():
    @task(task_id="generar_catalogo", execution_timeout=timedelta(minutes=5))
    def generar_catalogo() -> dict:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/actividades/generar-catalogo", timeout=120)
        resp.raise_for_status()
        resultado = resp.json()
        print(f"[ACTIVIDADES] {resultado}")
        return resultado

    generar_catalogo()


dag_instance = aerotrack_travel_catalogo_actividades()
