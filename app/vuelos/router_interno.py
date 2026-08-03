"""Endpoints internos de Vuelos — sin input de un actor humano directo,
disparados por scheduler (Airflow). Misma nota de seguridad que
`app/hoteles/router_interno.py`: en un despliegue real debe protegerse a
nivel de red o con token compartido; no implementado en esta sesión.

Enriquecimiento real del catálogo (AeroDataBox + Google Flights/SerpApi) —
corre DESPUÉS de la generación sintética de `dag_generar_catalogo_vuelos.py`
(`catalogo_vuelos_tasks.generar_vuelos_programables`, que sigue siendo la
base garantizada), nunca la reemplaza.
"""

from fastapi import APIRouter

from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.aerodatabox_client import AeroDataBoxApiClient
from app.vuelos.services.asientos_service import asignar_automaticamente
from app.vuelos.services.enriquecimiento_service import (
    enriquecer_con_aerodatabox,
    enriquecer_con_google_flights,
)
from app.vuelos.services.google_flights_client import GoogleFlightsApiClient

router = APIRouter(prefix="/internal/vuelos")


async def _cliente_aerodatabox() -> AeroDataBoxApiClient:
    repo = VuelosRepository()
    api_key = await repo.config("vuelos.aerodatabox_api_key")
    api_host = await repo.config("vuelos.aerodatabox_api_host")
    if not api_key or not api_host:
        raise RuntimeError("configuracion_sistema.vuelos.aerodatabox_api_key/api_host no está sembrado")
    return AeroDataBoxApiClient(api_key, api_host)


async def _cliente_google_flights() -> GoogleFlightsApiClient:
    repo = VuelosRepository()
    api_key = await repo.config("vuelos.google_flights_api_key")
    if not api_key:
        raise RuntimeError("configuracion_sistema.vuelos.google_flights_api_key no está sembrado")
    return GoogleFlightsApiClient(api_key)


@router.post("/enriquecer-aerodatabox")
async def enriquecer_aerodatabox_endpoint() -> dict:
    cliente = await _cliente_aerodatabox()
    return await enriquecer_con_aerodatabox(cliente)


@router.post("/enriquecer-google-flights")
async def enriquecer_google_flights_endpoint() -> dict:
    cliente = await _cliente_google_flights()
    return await enriquecer_con_google_flights(cliente)


@router.post("/asignar-asientos")
async def asignar_asientos_endpoint() -> dict:
    """RF-VUE-013 (CU-O117) — disparado por `dags/dag_asignar_asientos.py`."""
    asignados = await asignar_automaticamente()
    return {"asignados": asignados}
