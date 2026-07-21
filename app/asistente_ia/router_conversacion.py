"""RF-IA-001..006 (CU-O106..O111) — conversar (sesión opcional),
nueva conversación, historial (requiere sesión), calificar mensaje."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.asistente_ia.integrations.llm_client import GroqGeminiLLMClient
from app.asistente_ia.services.asistente_service import (
    MensajeInvalido,
    calificar_mensaje,
    conversar,
    historial_de_pasajero,
    nueva_conversacion,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import usuario_opcional, verificar_sesion
from app.shared.templating import templates

router = APIRouter(prefix="/asistente")


async def _pasajero_id(usuario: dict | None) -> str | None:
    if not usuario or usuario.get("tipo_actor") != "pasajero":
        return None
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    return pasajero["id"] if pasajero else None


@router.post("/conversar")
async def conversar_endpoint(mensaje: str = Form(...), usuario: dict | None = Depends(usuario_opcional)):
    pasajero_id = await _pasajero_id(usuario)
    resultado = await conversar(usuario, pasajero_id, mensaje, GroqGeminiLLMClient())
    return resultado


@router.post("/nueva-conversacion")
async def nueva_conversacion_endpoint(usuario: dict | None = Depends(usuario_opcional)):
    pasajero_id = await _pasajero_id(usuario)
    if pasajero_id:
        await nueva_conversacion(pasajero_id)
    return {"ok": True}


@router.get("/historial")
async def historial(request: Request, usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    conversaciones = await historial_de_pasajero(pasajero_id) if pasajero_id else []
    return templates.TemplateResponse(
        request, "historial_asistente.html", {"usuario": usuario, "conversaciones": conversaciones}
    )


@router.post("/mensajes/{mensaje_id}/calificar")
async def calificar(mensaje_id: str, calificacion: str = Form(...), usuario: dict | None = Depends(usuario_opcional)):
    if calificacion not in ("arriba", "abajo"):
        return {"ok": False, "motivo": "Calificación inválida"}
    try:
        await calificar_mensaje(usuario or {}, mensaje_id, calificacion)
    except MensajeInvalido as exc:
        return {"ok": False, "motivo": str(exc)}
    return {"ok": True}
