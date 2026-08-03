"""AeroTrack Travel — DAG: Marcar carritos abandonados (CU-T26)
===========================================================================
Qué hace: cada 15 minutos, dispara `POST /internal/carrito/marcar-abandonados`
en `app-travel`. Toda la lógica de negocio (RF-CAR-T01: marcar `abandonado`
un carrito `activo` inactivo más allá del umbral configurado y enviar el
email de recordatorio) vive en `app/carrito/services/abandono_service.py`
— este DAG es un disparador delgado, sin lógica propia, para que la
lógica real sea testeable con pytest en vez de solo dentro de un DAG.

UI: http://localhost:8081 -> busca "aerotrack_travel_marcar_carritos_abandonados"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de abandono de carrito")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_marcar_carritos_abandonados",
    description="CU-T26: marca carritos activo inactivos como abandonado y envía el recordatorio",
    schedule=timedelta(minutes=15),
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
    tags=["aerotrack-travel", "carrito", "app-travel"],
)
def aerotrack_travel_marcar_carritos_abandonados():
    @task(task_id="marcar_abandonados", execution_timeout=timedelta(minutes=2))
    def marcar_abandonados() -> int:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/carrito/marcar-abandonados", timeout=30)
        resp.raise_for_status()
        cantidad = resp.json()["marcados_abandonados"]
        print(f"[CARRITO] {cantidad} carrito(s) marcado(s) abandonado(s)")
        return cantidad

    marcar_abandonados()


dag_instance = aerotrack_travel_marcar_carritos_abandonados()
