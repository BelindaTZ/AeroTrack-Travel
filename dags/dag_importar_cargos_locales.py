"""AeroTrack Travel — DAG: Importar cargos locales de destino (RF-HOT-008/RN-HOT-003, CU-O59)
=================================================================================
Qué hace: dispara `POST /internal/hoteles/importar-cargos-locales` en
`app-travel`, que parsea `fuentes_extra/holidu_tourist_tax_por_ciudad.csv`
(snapshot de Holidu, ~100 ciudades) y hace upsert en `cargos_locales_destino`.
Toda la lógica real vive en `app/hoteles/services/cargos_locales_service.py`
— este DAG es un disparador delgado, mismo patrón que
`dag_generar_catalogo_hoteles.py`.

**Disparo manual, no periódico** (`schedule=None`): a diferencia del
catálogo de HotelLens, los datos de este CSV no cambian a diario — es un
snapshot importado una vez (o cuando se actualice el archivo a mano), no
una sincronización contra una API en vivo. `is_paused_upon_creation=True`
por la misma razón: no tiene sentido que corra sola en un cron.

UI: http://localhost:8081 -> busca "aerotrack_travel_cargos_locales"
"""

from __future__ import annotations

from datetime import timedelta

import requests
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import config


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de cargos locales")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_cargos_locales",
    description="RF-HOT-008/RN-HOT-003/CU-O59: importa cargos_locales_destino desde el CSV de Holidu",
    schedule=None,  # manual — no es una API con sincronización periódica
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    dagrun_timeout=timedelta(minutes=5),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "hoteles", "app-travel", "csv"],
)
def aerotrack_travel_cargos_locales():
    @task(task_id="importar_cargos_locales", execution_timeout=timedelta(minutes=3))
    def importar_cargos_locales() -> dict:
        resp = requests.post(f"{config.APP_TRAVEL_URL}/internal/hoteles/importar-cargos-locales", timeout=60)
        resp.raise_for_status()
        resultado = resp.json()
        print(f"[CARGOS_LOCALES] {resultado}")
        return resultado

    importar_cargos_locales()


dag_instance = aerotrack_travel_cargos_locales()
