"""RF-RES-006 (CU-O26) — crear alerta de precio."""

from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.services.alertas_precio_service import PasajeroNoEncontrado, crear_alerta
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates

router = APIRouter(prefix="/alertas-precio")


@router.get("")
async def listar_form(request: Request, usuario: dict = Depends(verificar_sesion)):
    repo = ReservasRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    alertas = await repo.listar_alertas_de_pasajero(pasajero["id"]) if pasajero else []
    return templates.TemplateResponse(
        request, "alertas_precio.html", {"usuario": usuario, "alertas": alertas}
    )


@router.post("")
async def crear(
    request: Request,
    origen: str = Form(...),
    destino: str = Form(...),
    fecha_objetivo: date = Form(...),
    precio_umbral: float = Form(...),
    usuario: dict = Depends(verificar_sesion),
):
    try:
        await crear_alerta(usuario, origen, destino, fecha_objetivo, precio_umbral)
    except PasajeroNoEncontrado:
        return templates.TemplateResponse(
            request,
            "alertas_precio.html",
            {"usuario": usuario, "alertas": [], "error": "Solo cuentas de pasajero pueden crear alertas."},
            status_code=400,
        )
    return RedirectResponse("/alertas-precio?mensaje=Alerta creada", status_code=303)
