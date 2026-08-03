"""
AeroTrack Travel — DAG: Generar catálogo de vuelos programables (CU-O30)
===========================================================================
Qué hace: cada día, asegura que exista un vuelo programado por cada ruta
curada (hubs reales, ver catalogo_vuelos_tasks.HUBS) para los próximos 7
días (ventana móvil), marca como 'completado' cualquier vuelo cuya llegada
programada ya pasó (CU-O31, versión sin API externa), y LUEGO enriquece
con datos reales de AeroDataBox (número de vuelo/horario/modelo de avión)
y Google Flights vía SerpApi (precio/emisiones CO2/predicciones) — este
enriquecimiento nunca es requisito de los dos primeros pasos, solo
reemplaza valores sintéticos cuando hay cupo real (ver
app/vuelos/services/enriquecimiento_service.py).

    [generar_vuelos] >> [actualizar_estados] >> [enriquecer_aerodatabox] >> [enriquecer_google_flights]

Fuente de rutas: dim_ruta en aerotrack-travel-dims (solo lectura).
Escribe en: vuelos_catalogo y tarifas_vuelo, en pocketbase-travel.

UI: http://localhost:8081 -> busca "aerotrack_travel_catalogo_vuelos"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config
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

    @task(task_id="enriquecer_aerodatabox", execution_timeout=timedelta(minutes=8))
    def enriquecer_aerodatabox(_actualizados: int) -> dict:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/vuelos/enriquecer-aerodatabox", timeout=120)
        resp.raise_for_status()
        resultado = resp.json()
        print(f"[VUELOS-AERODATABOX] {resultado}")
        return resultado

    @task(task_id="enriquecer_google_flights", execution_timeout=timedelta(minutes=8))
    def enriquecer_google_flights(_resultado_aerodatabox: dict) -> dict:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/vuelos/enriquecer-google-flights", timeout=120)
        resp.raise_for_status()
        resultado = resp.json()
        print(f"[VUELOS-GOOGLEFLIGHTS] {resultado}")
        return resultado

    creados = generar_vuelos()
    actualizados = actualizar_estados(creados)
    resultado_adb = enriquecer_aerodatabox(actualizados)
    enriquecer_google_flights(resultado_adb)


dag_instance = aerotrack_travel_catalogo_vuelos()
