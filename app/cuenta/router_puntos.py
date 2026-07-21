"""RF-CTA-006 — Consultar saldo y movimientos del programa de beneficios."""

from fastapi import APIRouter, Depends, Request

from app.cuenta.services.cuenta_service import resumen_puntos
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates

router = APIRouter()


@router.get("/mi-cuenta/puntos")
async def puntos(request: Request, usuario: dict = Depends(verificar_sesion)):
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    resumen = None
    if pasajero is not None:
        resumen = await resumen_puntos(pasajero["id"])
    return templates.TemplateResponse(request, "mi_cuenta_puntos.html", {"usuario": usuario, "resumen": resumen})
