"""AeroTrack Travel — DAG: Expirar reservas pendientes de pago (CU-O44)
===========================================================================
Qué hace: cada 5 minutos, dispara `POST /internal/reservas/expirar-pendientes`
en `app-travel`. Toda la lógica de negocio (RF-RES-007: cancelar reservas
`pendiente_pago` vencidas y liberar su cupo) vive en
`app/reservas/services/expiracion_service.py` — este DAG es un disparador
delgado, sin lógica propia, para que la lógica real sea testeable con
pytest en vez de solo dentro de un DAG.

UI: http://localhost:8081 -> busca "aerotrack_travel_expirar_reservas"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de expiración de reservas")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_expirar_reservas",
    description="CU-O44: cancela reservas pendiente_pago vencidas y libera su cupo",
    schedule=timedelta(minutes=5),
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
    tags=["aerotrack-travel", "reservas", "app-travel"],
)
def aerotrack_travel_expirar_reservas():
    @task(task_id="expirar_pendientes", execution_timeout=timedelta(minutes=2))
    def expirar_pendientes() -> int:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/reservas/expirar-pendientes", timeout=30)
        resp.raise_for_status()
        cantidad = resp.json()["expiradas"]
        print(f"[RESERVAS] {cantidad} reserva(s) expirada(s)")
        return cantidad

    expirar_pendientes()


dag_instance = aerotrack_travel_expirar_reservas()
