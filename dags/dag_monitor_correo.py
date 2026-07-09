"""
AeroTrack Travel — DAG: Monitorear bandeja de correo de la agencia (CU-O41/O42)
==================================================================================
Qué hace: confirma acceso a la bandeja de la agencia vía OAuth (Gmail API)
y busca correos recientes que coincidan con la heurística de "cambio de
itinerario" (gmail_monitor.PALABRAS_CLAVE_CAMBIO). Con una bandeja de
demostración recién creada es normal y esperado no encontrar coincidencias
reales — igual que el simulador estadístico (disrupciones_tasks.py) con
aerolíneas de buen desempeño histórico: cero resultados no es una falla
de la integración, es el resultado correcto para los datos actuales.

    [confirmar_identidad] >> [buscar_cambios_itinerario]

A diferencia del DAG de estado real (cuota escasa de AviationStack), la
cuota de Gmail API es generosa para este volumen — se registra en pausa
de todas formas, por el mismo criterio conservador: activar manualmente
una vez decidida la cadencia real de monitoreo.

Fuera de alcance (a propósito): crear la fila en disrupciones a partir de
un correo detectado requeriría parsear qué vuelo/reserva menciona el
correo (matching por número de vuelo o PNR) — con la heurística actual de
palabras clave alcanza para probar la integración, pero el parsing
estructurado se deja para cuando haya correos reales de aerolíneas que
inspeccionar. Igualmente fuera de alcance: el envío de la notificación
(CU-O43).

UI: http://localhost:8081 -> busca "aerotrack_travel_monitor_correo"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from gmail_monitor import detectar_cambios_itinerario, obtener_perfil


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de monitor de correo")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_monitor_correo",
    description="CU-O41/O42: monitorea la bandeja de la agencia vía Gmail API y detecta avisos de cambio de itinerario",
    schedule=None,  # activar manualmente con la cadencia deseada
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    dagrun_timeout=timedelta(minutes=10),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "disrupciones", "api-externa", "gmail"],
)
def aerotrack_travel_monitor_correo():
    @task(task_id="confirmar_identidad", execution_timeout=timedelta(seconds=30))
    def confirmar_identidad() -> dict:
        perfil = obtener_perfil()
        print(f"[MONITOR-CORREO] Buzón autenticado: {perfil.get('emailAddress')} "
              f"({perfil.get('messagesTotal')} mensajes totales)")
        return perfil

    @task(task_id="buscar_cambios_itinerario", execution_timeout=timedelta(minutes=5))
    def buscar_cambios_itinerario(_perfil: dict) -> int:
        candidatos = detectar_cambios_itinerario()
        for c in candidatos:
            print(f"[MONITOR-CORREO] posible cambio de itinerario: '{c['asunto']}' de {c['de']}")
        print(f"[MONITOR-CORREO] {len(candidatos)} correo(s) con posible cambio de itinerario")
        return len(candidatos)

    perfil = confirmar_identidad()
    buscar_cambios_itinerario(perfil)


dag_instance = aerotrack_travel_monitor_correo()
