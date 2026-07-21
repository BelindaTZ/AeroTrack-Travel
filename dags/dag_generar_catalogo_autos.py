"""AeroTrack Travel — DAG: Generar catálogo de autos (RF-AUT-004, CU-O119)
===========================================================================
Qué hace: dispara `POST /internal/autos/generar-catalogo` en `app-travel`.
Toda la lógica real (Global Rental Cars, sub-proveedor Expedia) vive en
`app/autos/services/catalogo_service.py` — este DAG es un disparador
delgado, mismo patrón que `dag_generar_catalogo_hoteles.py`.

A diferencia de HotelLens, Global Rental Cars no mostró rate limit
estricto en las pruebas (docs/apis-reference.md sección 8) — se activa por
defecto, cadencia diaria (`fuentes_datos_externas` sembró
`frecuencia_sincronizacion_horas = 24` para esta fuente).

UI: http://localhost:8081 -> busca "aerotrack_travel_catalogo_autos"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de catálogo de autos")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_catalogo_autos",
    description="RF-AUT-004/CU-O119: genera autos_catalogo vía Global Rental Cars (Expedia)",
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
    tags=["aerotrack-travel", "autos", "app-travel", "api-externa"],
)
def aerotrack_travel_catalogo_autos():
    @task(task_id="generar_catalogo", execution_timeout=timedelta(minutes=5))
    def generar_catalogo() -> dict:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/autos/generar-catalogo", timeout=120)
        resp.raise_for_status()
        resultado = resp.json()
        print(f"[AUTOS] {resultado}")
        return resultado

    generar_catalogo()


dag_instance = aerotrack_travel_catalogo_autos()
