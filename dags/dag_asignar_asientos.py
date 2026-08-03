"""AeroTrack Travel — DAG: Asignar asientos automáticamente (CU-O117)
===========================================================================
Qué hace: cada 30 minutos, dispara `POST /internal/vuelos/asignar-asientos`
en `app-travel`. Toda la lógica de negocio (RF-VUE-013: asignar un asiento
a todo pasajero confirmado sin elección propia cuya ventana de check-in
gratuito ya abrió) vive en `app/vuelos/services/asientos_service.py` — este
DAG es un disparador delgado, sin lógica propia, mismo patrón que
`dag_expirar_reservas_pendientes.py`.

UI: http://localhost:8081 -> busca "aerotrack_travel_asignar_asientos"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de asignación automática de asientos")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_asignar_asientos",
    description="CU-O117: asigna asiento automático a pasajeros confirmados que no eligieron a tiempo",
    schedule=timedelta(minutes=30),
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=5),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 2,
        "retry_delay": timedelta(minutes=1),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "vuelos", "app-travel"],
)
def aerotrack_travel_asignar_asientos():
    @task(task_id="asignar_pendientes", execution_timeout=timedelta(minutes=2))
    def asignar_pendientes() -> int:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/vuelos/asignar-asientos", timeout=60)
        resp.raise_for_status()
        cantidad = resp.json()["asignados"]
        print(f"[VUELOS] {cantidad} asiento(s) asignado(s) automáticamente")
        return cantidad

    asignar_pendientes()


dag_instance = aerotrack_travel_asignar_asientos()
