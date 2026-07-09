"""
AeroTrack Travel — DAG: Estimar riesgo de disrupción (simulador estadístico, CU-O39)
=======================================================================================
Qué hace: para vuelos programados fuera de la ventana de la API de estado
real (umbral configurable, configuracion_sistema.disrupciones.umbral_api_real_horas),
calcula un riesgo de disrupción a partir del histórico OTP/causas de retraso
(agg_otp_aerolinea_mes, agg_causas_retraso_mes en aerotrack-travel-dims) y
crea/actualiza la fila correspondiente en disrupciones.

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

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from disrupciones_tasks import estimar_riesgo_disrupcion


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
    dagrun_timeout=timedelta(minutes=20),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "disrupciones", "pocketbase-travel"],
)
def aerotrack_travel_riesgo_disrupcion():
    @task(task_id="estimar_riesgo", execution_timeout=timedelta(minutes=15))
    def estimar_riesgo() -> dict:
        return estimar_riesgo_disrupcion()

    estimar_riesgo()


dag_instance = aerotrack_travel_riesgo_disrupcion()
