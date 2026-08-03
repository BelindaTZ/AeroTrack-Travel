"""CU-T07 — cliente mínimo de solo lectura contra la REST API de Airflow
(auth básica, ya habilitada vía `AIRFLOW__API__AUTH_BACKENDS` en
docker-compose.yml). No usa el cliente Python de Airflow (no está
instalado en `app-travel`, solo en las imágenes de Airflow) — HTTP directo
con `httpx`, mismo patrón que las demás integraciones externas del
proyecto (ver `router_auth.py`)."""

import httpx

from app.shared.config import get_settings

DAG_CATALOGO_VUELOS = "aerotrack_travel_catalogo_vuelos"


class AirflowNoDisponible(Exception):
    pass


async def estado_dag(dag_id: str = DAG_CATALOGO_VUELOS, limite: int = 10) -> dict:
    """Último estado del DAG + sus corridas más recientes."""
    settings = get_settings()
    auth = (settings.airflow_user, settings.airflow_password)
    async with httpx.AsyncClient(base_url=settings.airflow_url, auth=auth, timeout=10.0) as cliente:
        try:
            resp_dag = await cliente.get(f"/api/v1/dags/{dag_id}")
            resp_runs = await cliente.get(
                f"/api/v1/dags/{dag_id}/dagRuns",
                params={"order_by": "-execution_date", "limit": limite},
            )
        except httpx.HTTPError as exc:
            raise AirflowNoDisponible(str(exc)) from exc

    if resp_dag.status_code != 200 or resp_runs.status_code != 200:
        raise AirflowNoDisponible(f"Airflow respondió {resp_dag.status_code}/{resp_runs.status_code}")

    dag = resp_dag.json()
    corridas = resp_runs.json().get("dag_runs", [])
    return {
        "dag_id": dag_id,
        "is_paused": dag.get("is_paused"),
        "ultima_corrida": corridas[0] if corridas else None,
        "corridas": corridas,
    }
