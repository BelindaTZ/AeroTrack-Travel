"""RF-PAS-002 / CU-O15 — Editar datos de contacto."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.pasajeros.services.pasajeros_service import (
    PasajeroNoEncontrado,
    TelefonoInvalido,
    actualizar_contacto,
)
from app.seguridad.services.session_service import verificar_sesion

router = APIRouter()


@router.post("/mi-perfil/contacto")
async def editar_contacto(
    request: Request,
    telefono: str = Form(...),
    direccion: str | None = Form(None),
    contacto_emergencia: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
):
    try:
        await actualizar_contacto(usuario, telefono, direccion=direccion, contacto_emergencia=contacto_emergencia)
    except TelefonoInvalido as e:
        return RedirectResponse(f"/mi-perfil?mensaje={str(e)}", status_code=303)
    except PasajeroNoEncontrado:
        return RedirectResponse("/mi-perfil?mensaje=Perfil+de+pasajero+no+encontrado", status_code=303)

    return RedirectResponse("/mi-perfil?mensaje=Contacto+actualizado", status_code=303)