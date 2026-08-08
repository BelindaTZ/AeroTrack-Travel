"""
AeroTrack Travel — DAG: Narrativa automática con IA para dashboards estratégicos
====================================================================================
Esqueleto sin lógica todavía (docs/estrategico-auditoria.md Fase C /
pedido explícito del usuario, semana siguiente) — las 3 tareas están
vacías (`pass`) a propósito. Creado `is_paused_upon_creation=True`: no
correr con schedule real hasta que tarea_2 tenga una llamada real a
`GroqGeminiLLMClient` (`app/asistente_ia/integrations/llm_client.py`, ya
verificado en Fase B con las credenciales sembradas en
`configuracion_sistema`).

Diseño previsto para cuando se implemente (no implementado acá):
- tarea_1 (`extraer_kpis_estrategicos`): llamar los endpoints
  `/backoffice/estrategico/{cockpit,oferta,disrupciones,inteligencia}/datos`
  (o un endpoint interno dedicado) para juntar los KPIs de los 4 DS.
- tarea_2 (`generar_narrativa_llm`): armar el prompt con esos KPIs y
  llamar `GroqGeminiLLMClient.generar()` — mismo patrón "DAG delgado que
  llama a un endpoint interno de la app" que ya usa
  `dag_estimar_riesgo_disrupcion.py`, no lógica de LLM directo en Airflow.
- tarea_3 (`guardar_narrativa_clickhouse`): persistir el texto generado
  (tabla ClickHouse nueva o blob en MinIO, a decidir) para que los 4
  dashboards estratégicos lo consuman sin regenerarlo en cada request.

UI: http://localhost:8081 -> busca "aerotrack_travel_elt_narrativa_ia"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN aerotrack_travel_elt_narrativa_ia")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_elt_narrativa_ia",
    description="[Esqueleto] Narrativa automática con IA para los dashboards estratégicos DS-00 a DS-03",
    schedule="@hourly",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,  # no activar hasta implementar tarea_2 (llamada real al LLM)
    dagrun_timeout=timedelta(minutes=30),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "elt", "estrategico", "asistente-ia", "esqueleto"],
)
def aerotrack_travel_elt_narrativa_ia():
    @task(task_id="extraer_kpis_estrategicos")
    def extraer_kpis_estrategicos() -> None:
        pass

    @task(task_id="generar_narrativa_llm")
    def generar_narrativa_llm() -> None:
        pass

    @task(task_id="guardar_narrativa_clickhouse")
    def guardar_narrativa_clickhouse() -> None:
        pass

    guardar_narrativa_clickhouse_task = guardar_narrativa_clickhouse()
    generar_narrativa_llm_task = generar_narrativa_llm()
    extraer_kpis_estrategicos_task = extraer_kpis_estrategicos()

    extraer_kpis_estrategicos_task >> generar_narrativa_llm_task >> guardar_narrativa_clickhouse_task


dag_instance = aerotrack_travel_elt_narrativa_ia()
