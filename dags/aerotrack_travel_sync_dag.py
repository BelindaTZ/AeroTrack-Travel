"""
AeroTrack Travel -- DAG puente: sincroniza el modelo dimensional desde Analytics
===================================================================================
Que hace: permite al administrador de Travel disparar (manual o programado)
el pipeline ELT completo de AeroTrack Analytics (proyecto minio-elt) junto
con la extension de cobertura mundial, y trae el resultado a minio-travel
(la instancia MinIO propia de Travel).

    [asegurar_analytics_arriba] -> [disparar_elt] -> [disparar_cobertura_global] -> [sincronizar_a_travel]

La primera tarea arranca (si hace falta) solo los 5 contenedores de
Analytics estrictamente necesarios (postgres-airflow, minio, pocketbase,
airflow-webserver, airflow-scheduler) via el socket de Docker del host,
montado unicamente en airflow-scheduler-travel. No toca prometheus/
grafana/fastapi-app/aerotrack-setup.

IMPORTANTE sobre el orden: el paso "transform" del ELT de Analytics
RECONSTRUYE dim_aeropuerto/dim_aerolinea/dim_ruta desde cero a partir de
los datos BTS en cada corrida -- si se sincronizara antes de correr el
DAG de cobertura global, se perderia esa extension mundial. Por eso el
orden es siempre: ELT primero, cobertura global despues, sync al final.

El horario se lee de la Airflow Variable `travel_sync_schedule` (mismo
patron que `pipeline_schedule` en el ELT de Analytics), configurable
desde Admin > Variables en la UI de Airflow de Travel:
  - "manual" o vacio -> schedule=None (solo manual, boton Trigger DAG)
  - preset (@daily, @weekly, @monthly) o expresion cron -> se usa directo

No es una dependencia permanente de Travel: solo ESTE DAG especifico
necesita que Analytics (su Airflow y su MinIO) esten corriendo, y
unicamente mientras se ejecuta. El resto de Travel (pocketbase-travel,
app-travel, minio-travel) funciona sin Analytics.

UI: http://localhost:8081 -> busca "aerotrack_travel_sync_dims"
"""

from __future__ import annotations

from datetime import timedelta

from aerotrack_travel_sync_tasks import asegurar_analytics_arriba, disparar_dag_analytics, sincronizar_dims_a_travel
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.utils.dates import days_ago


def _get_schedule() -> str | None:
    raw = Variable.get("travel_sync_schedule", default_var="manual")
    if not raw or raw.strip() == "" or raw.strip() == "manual":
        return None
    return raw.strip()


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    exception = context.get("exception")
    print("FALLO EN aerotrack_travel_sync_dims")
    print(f"   Tarea: {ti.task_id}")
    print(f"   Error: {exception}")


@dag(
    dag_id="aerotrack_travel_sync_dims",
    description="Dispara el ELT + cobertura global de Analytics y sincroniza el resultado a minio-travel",
    schedule=_get_schedule(),
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=4),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack", "travel", "sync", "analytics", "minio"],
)
def aerotrack_travel_sync_dims():
    """
    DAG puente Travel -> Analytics -> Travel.

    Orden estricto:
    asegurar_analytics_arriba >> disparar_elt >> disparar_cobertura_global >> sincronizar_a_travel
    """

    @task(task_id="asegurar_analytics_arriba", execution_timeout=timedelta(minutes=5))
    def asegurar_arriba() -> None:
        asegurar_analytics_arriba()

    @task(task_id="disparar_elt", execution_timeout=timedelta(hours=2))
    def disparar_elt(_listo: None) -> str:
        return disparar_dag_analytics("aerotrack_elt_pipeline", timeout_minutos=90)

    @task(task_id="disparar_cobertura_global", execution_timeout=timedelta(minutes=30))
    def disparar_cobertura_global(_estado_elt: str) -> str:
        return disparar_dag_analytics("aerotrack_extend_global_dims", timeout_minutos=20)

    @task(task_id="sincronizar_a_travel", execution_timeout=timedelta(minutes=15))
    def sincronizar_a_travel(_estado_global: str) -> dict:
        return sincronizar_dims_a_travel()

    listo = asegurar_arriba()
    estado_elt = disparar_elt(listo)
    estado_global = disparar_cobertura_global(estado_elt)
    sincronizar_a_travel(estado_global)


dag_instance = aerotrack_travel_sync_dims()
