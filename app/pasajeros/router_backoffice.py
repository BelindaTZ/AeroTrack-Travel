"""RF-PAS-003, 004 / CU-O16 — Backoffice: buscar y gestionar pasajeros."""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.pasajeros.services.pasajeros_service import (
    PasajeroNoEncontrado,
    buscar_pasajeros_backoffice,
    editar_contacto_backoffice,
    obtener_detalle_pasajero,
)
from app.seguridad.services.rbac_service import requiere_permiso
from app.seguridad.services.session_service import verificar_sesion
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/pasajeros")


async def _rbac_ver(usuario: dict = Depends(requiere_permiso("pasajeros", "ver", "pasajeros"))):
    return usuario


async def _rbac_editar(usuario: dict = Depends(requiere_permiso("pasajeros", "editar", "pasajeros"))):
    return usuario


@router.get("")
async def buscar_pasajeros(
    request: Request,
    q: str = Query(""),
    usuario: dict = Depends(_rbac_ver),
):
    resultados = []
    if q:
        resultados = await buscar_pasajeros_backoffice(usuario, q)
    contexto = await nav_context(usuario)
    return templates.TemplateResponse(
        request,
        "backoffice/buscar_pasajeros.html",
        {**contexto, "resultados": resultados, "q": q},
    )


@router.get("/{pasajero_id}")
async def detalle_pasajero(
    request: Request,
    pasajero_id: str,
    usuario: dict = Depends(_rbac_ver),
):
    detalle = await obtener_detalle_pasajero(usuario, pasajero_id)
    contexto = await nav_context(usuario)
    if detalle is None:
        return templates.TemplateResponse(
            request,
            "backoffice/detalle_pasajero.html",
            {**contexto, "pasajero": None},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "backoffice/detalle_pasajero.html",
        {**contexto, "pasajero": detalle},
    )


@router.put("/{pasajero_id}")
async def editar_pasajero(
    request: Request,
    pasajero_id: str,
    telefono: str = Form(None),
    direccion: str | None = Form(None),
    contacto_emergencia: str | None = Form(None),
    usuario: dict = Depends(_rbac_editar),
):
    data = {}
    if telefono is not None:
        data["telefono"] = telefono
    if direccion is not None:
        data["direccion"] = direccion
    if contacto_emergencia is not None:
        data["contacto_emergencia"] = contacto_emergencia

    try:
        actualizado = await editar_contacto_backoffice(usuario, pasajero_id, data)
    except PasajeroNoEncontrado:
        return JSONResponse(status_code=404, content={"detail": "Pasajero no encontrado"})

    return JSONResponse(
        {
            "id": actualizado["id"],
            "telefono": actualizado.get("telefono"),
            "direccion": actualizado.get("direccion"),
            "contacto_emergencia": actualizado.get("contacto_emergencia"),
        }
    )