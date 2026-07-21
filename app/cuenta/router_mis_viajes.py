"""RF-CTA-001 — Ver Mis Viajes, agrupadas por próxima/activa/pasada."""

from fastapi import APIRouter, Depends, Request

from app.cuenta.services.cuenta_service import mis_viajes_agrupados
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates

router = APIRouter()


@router.get("/mis-viajes")
async def mis_viajes(request: Request, usuario: dict = Depends(verificar_sesion)):
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    grupos = {"proximas": [], "activas": [], "pasadas": [], "sin_fecha": []}
    if pasajero is not None:
        grupos = await mis_viajes_agrupados(pasajero["id"])
    return templates.TemplateResponse(request, "mis_viajes.html", {"usuario": usuario, "grupos": grupos})
