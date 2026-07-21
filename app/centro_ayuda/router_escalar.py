"""RF-AYU-004 (CU-O100) — escalar caso no resuelto a agente humano vía
email (RN-AYU-001: requiere sesión activa, a diferencia de calificar)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.centro_ayuda.integrations.escalacion_sender import GmailEscalacionSender
from app.centro_ayuda.services.centro_ayuda_service import escalar_caso
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import verificar_sesion

router = APIRouter(prefix="/ayuda")


@router.post("/escalar")
async def escalar(
    request: Request,
    asunto: str = Form(...),
    mensaje: str = Form(...),
    next: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
):
    destino = next or "/ayuda/buscar"
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        return RedirectResponse(
            f"{destino}?mensaje=Solo cuentas de pasajero pueden escalar un caso", status_code=303
        )

    await escalar_caso(usuario, pasajero["id"], asunto, mensaje, GmailEscalacionSender())
    return RedirectResponse(
        f"{destino}?mensaje=Caso escalado — nuestro equipo te responderá por email", status_code=303
    )
