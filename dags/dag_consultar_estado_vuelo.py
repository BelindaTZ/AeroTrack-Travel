"""AeroTrack Travel — DAG: Consultar estado real de vuelo (CU-O27)
===========================================================================
Qué hace: dispara `POST /internal/disrupciones/consultar-api` en
`app-travel`. Toda la lógica vive en
`app/disrupciones/services/api_estado_vuelo_service.py` — este DAG es un
disparador delgado.

Frecuencia deliberadamente baja (cada 6 horas, no cada pocos minutos): la
cuota mensual real de AviationStack está configurada en
`configuracion_sistema.api_estado_vuelo.limite_mensual` (90/mes) y cada
corrida puede consultar varios vuelos a la vez — un intervalo corto la
agotaría en pocos días.

UI: http://localhost:8081 -> busca "aerotrack_travel_consultar_estado_vuelo"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de consulta de estado real de vuelo")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_consultar_estado_vuelo",
    description="CU-O27: consulta la API real de estado de vuelo para reservas confirmadas cercanas",
    schedule=timedelta(hours=6),
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
def aerotrack_travel_consultar_estado_vuelo():
    @task(task_id="consultar_api", execution_timeout=timedelta(minutes=3))
    def consultar_api() -> dict:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/disrupciones/consultar-api", timeout=60)
        resp.raise_for_status()
        resumen = resp.json()
        print(f"[DISRUPCIONES] {resumen}")
        return resumen

    consultar_api()


dag_instance = aerotrack_travel_consultar_estado_vuelo()
