"""AeroTrack Travel — DAG: Generar catálogo de hoteles (RF-HOT-004/005, CU-O118)
===========================================================================
Qué hace: dispara `POST /internal/hoteles/generar-catalogo` en `app-travel`.
Toda la lógica real (flujo de 3 pasos de HotelLens + reseñas) vive en
`app/hoteles/services/catalogo_service.py` — este DAG es un disparador
delgado, sin lógica propia, mismo patrón que
`dag_expirar_reservas_pendientes.py`.

Frecuencia: cada 12h (`configuracion_sistema` / `fuentes_datos_externas`
sembró `HotelLens.frecuencia_sincronizacion_horas = 12`, ver
`scripts/seed_fuentes_datos_externas.py`) — el rate limit estricto del plan
BASIC de HotelLens (~4-5 llamadas/min) es la razón real de no ir más
seguido, no una preferencia arbitraria.

UI: http://localhost:8081 -> busca "aerotrack_travel_catalogo_hoteles"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de catálogo de hoteles")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_catalogo_hoteles",
    description="RF-HOT-004/005/CU-O118: genera hoteles_catalogo/hoteles_tarifas y cachea hoteles_resenas vía HotelLens",
    schedule=timedelta(hours=12),
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,  # activar manualmente — cada corrida gasta cuota real de HotelLens
    dagrun_timeout=timedelta(minutes=10),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "hoteles", "app-travel", "api-externa"],
)
def aerotrack_travel_catalogo_hoteles():
    @task(task_id="generar_catalogo", execution_timeout=timedelta(minutes=5))
    def generar_catalogo() -> dict:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/hoteles/generar-catalogo", timeout=120)
        resp.raise_for_status()
        resultado = resp.json()
        print(f"[HOTELES] {resultado}")
        return resultado

    generar_catalogo()


dag_instance = aerotrack_travel_catalogo_hoteles()
