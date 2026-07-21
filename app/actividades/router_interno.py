"""Endpoint interno de Actividades — disparado por scheduler (Airflow),
sin input de un actor humano directo. Misma nota de seguridad que
`app/reservas/router_interno.py`."""

from fastapi import APIRouter

from app.actividades.repositories.actividades_repo import ActividadesRepository
from app.actividades.services.catalogo_service import generar_catalogo
from app.actividades.services.traveladvisor_client import TravelAdvisorApiClient

router = APIRouter(prefix="/internal/actividades")


async def _cliente_real() -> TravelAdvisorApiClient:
    repo = ActividadesRepository()
    api_key = await repo.config("actividades.rapidapi_key")
    api_host = await repo.config("actividades.rapidapi_host")
    if not api_key or not api_host:
        raise RuntimeError("configuracion_sistema.actividades.rapidapi_key/rapidapi_host no está sembrado")
    return TravelAdvisorApiClient(api_key, api_host)


@router.post("/generar-catalogo")
async def generar_catalogo_endpoint() -> dict:
    cliente = await _cliente_real()
    return await generar_catalogo(cliente)
