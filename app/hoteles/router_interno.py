"""Endpoint interno de Hoteles — sin input de un actor humano directo,
disparado por scheduler (Airflow). Misma nota de seguridad que
`app/reservas/router_interno.py`: en un despliegue real debe protegerse a
nivel de red o con token compartido; no implementado en esta sesión.
"""

from pathlib import Path

from fastapi import APIRouter

from app.hoteles.repositories.hoteles_repo import HotelesRepository
from app.hoteles.services.cargos_locales_service import importar_cargos_locales
from app.hoteles.services.catalogo_service import generar_catalogo
from app.hoteles.services.hotellens_client import HotelLensApiClient

router = APIRouter(prefix="/internal/hoteles")

_CSV_CARGOS_LOCALES = Path(__file__).resolve().parent.parent.parent / "fuentes_extra" / "holidu_tourist_tax_por_ciudad.csv"


async def _cliente_real() -> HotelLensApiClient:
    repo = HotelesRepository()
    api_key = await repo.config("hoteles.rapidapi_key")
    api_host = await repo.config("hoteles.rapidapi_host")
    if not api_key or not api_host:
        raise RuntimeError("configuracion_sistema.hoteles.rapidapi_key/rapidapi_host no está sembrado")
    return HotelLensApiClient(api_key, api_host)


@router.post("/generar-catalogo")
async def generar_catalogo_endpoint() -> dict:
    cliente = await _cliente_real()
    return await generar_catalogo(cliente)


@router.post("/importar-cargos-locales")
async def importar_cargos_locales_endpoint() -> dict:
    """RF-HOT-008/RN-HOT-003 — disparo manual/infrecuente, no un ciclo
    periódico (los datos del CSV no cambian a diario)."""
    return await importar_cargos_locales(str(_CSV_CARGOS_LOCALES))
