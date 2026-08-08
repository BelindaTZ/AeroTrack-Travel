"""
AeroTrack Travel — DAG: ELT asistente IA -> ClickHouse
=========================================================
docs/estrategico-auditoria.md Fase B.3 — sexto DAG del pipeline de
ClickHouse, primero construido para el nivel ESTRATÉGICO (DS-03). Alimenta
`agg_uso_asistente_ia` desde mensajes_ia/conversaciones_ia (vía
`/internal/analitica`). Ver `aerotrack_travel_elt_asistente_ia_tasks.py`
para los gaps reales de esquema (sin `categoria`, `calificacion` binaria
no 1-5) y el acoplamiento documentado con
`app/asistente_ia/services/asistente_service.py::_MARCADORES_SIN_RESPUESTA`.

UI: http://localhost:8081 -> busca "aerotrack_travel_elt_asistente_ia"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from aerotrack_travel_elt_asistente_ia_tasks import cargar, extraer, transformar


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN aerotrack_travel_elt_asistente_ia")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_elt_asistente_ia",
    description="Carga agg_uso_asistente_ia en ClickHouse (soporta DS-03)",
    schedule="@hourly",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=30),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "elt", "clickhouse", "estrategico", "asistente-ia"],
)
def aerotrack_travel_elt_asistente_ia():
    @task(task_id="extraer", execution_timeout=timedelta(minutes=10))
    def _extraer() -> dict:
        return extraer()

    @task(task_id="transformar", execution_timeout=timedelta(minutes=10))
    def _transformar(extraido: dict) -> dict:
        return transformar(extraido)

    @task(task_id="cargar", execution_timeout=timedelta(minutes=10))
    def _cargar(transformado: dict) -> dict:
        return cargar(transformado)

    _cargar(_transformar(_extraer()))


dag_instance = aerotrack_travel_elt_asistente_ia()
