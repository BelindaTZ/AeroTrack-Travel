"""AeroTrack Travel — DAG: Monitorear bandeja de correo (CU-O28)
===========================================================================
Qué hace: cada 15 minutos, dispara `POST /internal/disrupciones/monitorear-correo`
en `app-travel`. Toda la lógica vive en
`app/disrupciones/services/monitor_correo_service.py` — este DAG es un
disparador delgado.

UI: http://localhost:8081 -> busca "aerotrack_travel_monitorear_correo"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de monitoreo de correo")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_monitorear_correo",
    description="CU-O28/O29: monitorea la bandeja de correo de la agencia y detecta cambios de itinerario",
    schedule=timedelta(minutes=15),
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=5),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "disrupciones", "app-travel"],
)
def aerotrack_travel_monitorear_correo():
    @task(task_id="monitorear_correo", execution_timeout=timedelta(minutes=3))
    def monitorear_correo() -> dict:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/disrupciones/monitorear-correo", timeout=60)
        resp.raise_for_status()
        resumen = resp.json()
        print(f"[DISRUPCIONES] {resumen}")
        return resumen

    monitorear_correo()


dag_instance = aerotrack_travel_monitorear_correo()
