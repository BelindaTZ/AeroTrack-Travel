"""RF-PAS-005 (CU-O49) — documentos de viaje. RF-PAS-006 (CU-O50) — viajeros
frecuentes. Ambos: autoservicio del propio pasajero desde /mi-perfil."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.pasajeros.services.pasajeros_service import (
    PasajeroNoEncontrado,
    SinPermiso,
    TipoDocumentoInvalido,
    crear_documento_viaje,
    crear_viajero_frecuente,
    eliminar_documento_viaje,
    eliminar_viajero_frecuente,
)
from app.seguridad.services.session_service import verificar_sesion

router = APIRouter()


@router.post("/mi-perfil/documentos")
async def agregar_documento(
    request: Request,
    tipo: str = Form(...),
    numero: str = Form(...),
    pais_emision: str = Form(...),
    fecha_vencimiento: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
):
    try:
        await crear_documento_viaje(usuario, tipo, numero, pais_emision, fecha_vencimiento or None)
    except TipoDocumentoInvalido:
        return RedirectResponse("/mi-perfil?mensaje=Tipo+de+documento+no+válido", status_code=303)
    except PasajeroNoEncontrado:
        return RedirectResponse("/mi-perfil?mensaje=Perfil+de+pasajero+no+encontrado", status_code=303)
    return RedirectResponse("/mi-perfil?mensaje=Documento+agregado", status_code=303)


@router.post("/mi-perfil/documentos/{documento_id}/eliminar")
async def quitar_documento(
    request: Request, documento_id: str, usuario: dict = Depends(verificar_sesion)
):
    try:
        await eliminar_documento_viaje(usuario, documento_id)
    except (SinPermiso, PasajeroNoEncontrado):
        return RedirectResponse("/mi-perfil?mensaje=No+se+pudo+eliminar+el+documento", status_code=303)
    return RedirectResponse("/mi-perfil?mensaje=Documento+eliminado", status_code=303)


@router.post("/mi-perfil/viajeros-frecuentes")
async def agregar_viajero_frecuente(
    request: Request,
    nombre_completo: str = Form(...),
    fecha_nacimiento: str | None = Form(None),
    numero_documento: str | None = Form(None),
    relacion: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
):
    try:
        await crear_viajero_frecuente(
            usuario, nombre_completo, fecha_nacimiento or None, numero_documento or None, relacion or None
        )
    except PasajeroNoEncontrado:
        return RedirectResponse("/mi-perfil?mensaje=Perfil+de+pasajero+no+encontrado", status_code=303)
    return RedirectResponse("/mi-perfil?mensaje=Viajero+frecuente+agregado", status_code=303)


@router.post("/mi-perfil/viajeros-frecuentes/{viajero_id}/eliminar")
async def quitar_viajero_frecuente(
    request: Request, viajero_id: str, usuario: dict = Depends(verificar_sesion)
):
    try:
        await eliminar_viajero_frecuente(usuario, viajero_id)
    except (SinPermiso, PasajeroNoEncontrado):
        return RedirectResponse("/mi-perfil?mensaje=No+se+pudo+eliminar+el+viajero+frecuente", status_code=303)
    return RedirectResponse("/mi-perfil?mensaje=Viajero+frecuente+eliminado", status_code=303)
