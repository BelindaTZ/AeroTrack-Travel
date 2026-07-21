"""Endpoint interno de Cruceros — disparado por scheduler (Airflow), sin
input de un actor humano directo. Misma nota de seguridad que
`app/reservas/router_interno.py`."""

from fastapi import APIRouter

from app.cruceros.repositories.cruceros_repo import CrucerosRepository
from app.cruceros.services.catalogo_service import generar_catalogo
from app.cruceros.services.cruisepricing_client import CruisePricingApiClient

router = APIRouter(prefix="/internal/cruceros")


async def _cliente_real() -> CruisePricingApiClient:
    repo = CrucerosRepository()
    api_key = await repo.config("cruceros.rapidapi_key")
    api_host = await repo.config("cruceros.rapidapi_host")
    if not api_key or not api_host:
        raise RuntimeError("configuracion_sistema.cruceros.rapidapi_key/rapidapi_host no está sembrado")
    return CruisePricingApiClient(api_key, api_host)


@router.post("/generar-catalogo")
async def generar_catalogo_endpoint() -> dict:
    cliente = await _cliente_real()
    return await generar_catalogo(cliente)
