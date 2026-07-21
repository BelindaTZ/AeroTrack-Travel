"""Endpoint interno de Autos — disparado por scheduler (Airflow), sin
input de un actor humano directo. Misma nota de seguridad que
`app/reservas/router_interno.py`."""

from fastapi import APIRouter

from app.autos.repositories.autos_repo import AutosRepository
from app.autos.services.catalogo_service import generar_catalogo
from app.autos.services.rentalcars_client import RentalCarsApiClient

router = APIRouter(prefix="/internal/autos")


async def _cliente_real() -> RentalCarsApiClient:
    repo = AutosRepository()
    api_key = await repo.config("autos.rapidapi_key")
    api_host = await repo.config("autos.rapidapi_host")
    if not api_key or not api_host:
        raise RuntimeError("configuracion_sistema.autos.rapidapi_key/rapidapi_host no está sembrado")
    return RentalCarsApiClient(api_key, api_host)


@router.post("/generar-catalogo")
async def generar_catalogo_endpoint() -> dict:
    cliente = await _cliente_real()
    return await generar_catalogo(cliente)
