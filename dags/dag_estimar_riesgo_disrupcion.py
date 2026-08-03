"""
AeroTrack Travel — DAG: Estimar riesgo de disrupción (simulador estadístico, CU-O39)
=======================================================================================
Qué hace: dispara `POST /internal/disrupciones/estimar-riesgo` en
`app-travel`. Toda la lógica vive en
`app/disrupciones/services/riesgo_service.py` — este DAG es un disparador
delgado (paso 6 del plan de migración: `disrupciones` ya vive en MinIO, y
solo la app tiene acceso a `DisrupcionesRepository`/
`minio_operational_client`; el DAG ya no puede escribir la colección
directo vía `dags/pocketbase_client.py` como antes).

Corre después del DAG de catálogo (depende de que existan vuelos_catalogo
para evaluar), pero no lo dispara directamente — se agenda con un pequeño
desfase horario para evitar condiciones de carrera en la misma corrida diaria.

Fuera de alcance (adrede): el envío de la notificación al pasajero (CU-O43)
y las otras dos fuentes de detección (API real CU-O40, monitor de correo
CU-O41) — dependen de integraciones externas (CU-O17/O18) aún no configuradas.

UI: http://localhost:8081 -> busca "aerotrack_travel_riesgo_disrupcion"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de riesgo de disrupción")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_riesgo_disrupcion",
    description="CU-O39: estima riesgo de disrupción con el simulador estadístico (histórico BTS/FAA)",
    schedule="@daily",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=10),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "disrupciones", "app-travel"],
)
def aerotrack_travel_riesgo_disrupcion():
    @task(task_id="estimar_riesgo", execution_timeout=timedelta(minutes=5))
    def estimar_riesgo() -> dict:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/disrupciones/estimar-riesgo", timeout=180)
        resp.raise_for_status()
        resumen = resp.json()
        print(f"[DISRUPCION-SIM] {resumen}")
        return resumen

    estimar_riesgo()


dag_instance = aerotrack_travel_riesgo_disrupcion()
