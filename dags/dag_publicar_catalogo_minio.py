"""
AeroTrack Travel — DAG: Publicar catálogo STAGING a MinIO (ETAPA 1 de la
migración PocketBase-staging -> MinIO-operacional/catálogo)
===========================================================================
Qué hace: cada día, después de que corren los DAGs de generación de
catálogo (`aerotrack_travel_catalogo_vuelos/hoteles/autos/actividades/
cruceros`, `aerotrack_travel_cargos_locales`, `aerotrack_travel_tasas_
cambio`), vuelca cada colección STAGING de pocketbase-travel como NDJSON
en el bucket `aerotrack-travel-catalog` (MinIO). No modifica nada en
PocketBase — es un ETL de solo lectura sobre staging, escritura sobre
MinIO. Los router_busqueda.py de la app leen de ahí (ver plan de
migración PASO 3).

No se encadena con sensores a los DAGs de generación (distintos horarios,
algunos manuales/pausados) — corre en su propio @daily y refleja lo que
haya en PocketBase en ese momento, aceptable para un catálogo de búsqueda
que ya se regenera a diario.

UI: http://localhost:8081 -> busca "aerotrack_travel_publicar_catalogo"
"""

from __future__ import annotations

from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

from catalogo_minio_publisher import publicar_grupo

GRUPOS: dict[str, list[str]] = {
    "vuelos": ["aerolineas", "vuelos_catalogo", "tarifas_vuelo", "predicciones_precio_ruta", "asientos_vuelo"],
    "hoteles": ["hoteles_catalogo", "hoteles_tarifas", "hoteles_resenas", "hoteles_disponibilidad"],
    "autos": ["autos_catalogo", "autos_disponibilidad"],
    "actividades": ["actividades_catalogo", "actividades_horarios", "actividades_resenas"],
    "cruceros": ["navieras", "barcos", "cruceros_catalogo", "cruceros_camarotes_tarifa"],
    "cargos_locales": ["cargos_locales_destino"],
    "tasas_cambio": ["tasas_cambio"],
    "visa": ["requisitos_visa_cache"],
}


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de publicación de catálogo a MinIO")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_publicar_catalogo",
    description="ETAPA 1 migración: publica colecciones STAGING de pocketbase-travel como NDJSON en aerotrack-travel-catalog",
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
    tags=["aerotrack-travel", "migracion-bd", "minio-catalogo"],
)
def aerotrack_travel_publicar_catalogo():
    for nombre_grupo, colecciones in GRUPOS.items():
        @task(task_id=f"publicar_{nombre_grupo}", execution_timeout=timedelta(minutes=5))
        def publicar(colecciones=colecciones, nombre_grupo=nombre_grupo) -> dict:
            resultado = publicar_grupo(colecciones)
            print(f"[CATALOGO-MINIO] {nombre_grupo}: {resultado}")
            return resultado

        publicar()


dag_instance = aerotrack_travel_publicar_catalogo()
