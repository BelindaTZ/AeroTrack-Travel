"""RF-PAS-001 / CU-O14 — Consultar historial de reservas propio."""

from fastapi import APIRouter, Depends, Query, Request

from app.pasajeros.services.pasajeros_service import obtener_historial
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates

router = APIRouter()


@router.get("/mis-reservas")
async def mis_reservas(
    request: Request,
    estado: str | None = Query(None),
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    usuario: dict = Depends(verificar_sesion),
):
    reservas = await obtener_historial(usuario, estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    return templates.TemplateResponse(
        request,
        "historial_reservas.html",
        {
            "usuario": usuario,
            "reservas": reservas,
            "filtro_estado": estado,
            "filtro_desde": fecha_desde,
            "filtro_hasta": fecha_hasta,
        },
    )