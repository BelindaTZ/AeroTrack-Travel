"""Endpoints internos de Facturación — sin input de un actor humano directo
(mismo patrón y misma nota de seguridad que `app/reservas/router_interno.py`:
en un despliegue real deben protegerse a nivel de red o con token compartido).

El camino de producción real (Reservas -> Facturación) es una llamada
in-process directa a estos servicios, no HTTP — estos endpoints existen
para consumidores futuros (backoffice, Disrupciones) que si necesiten HTTP.
"""

from fastapi import APIRouter, Form, HTTPException

from app.facturacion.services.diferencia_tarifa_service import (
    CobroDiferenciaRechazado,
    PagoOriginalNoEncontrado,
    cobrar_o_reembolsar_diferencia,
)
from app.facturacion.services.reembolso_service import (
    PagoNoEncontrado,
    ReembolsoNoAplicable,
    procesar_reembolso,
)

router = APIRouter(prefix="/internal")


@router.post("/reembolsos")
async def reembolsos_endpoint(reserva_id: str = Form(...), motivo: str = Form(...)) -> dict:
    try:
        reembolso = await procesar_reembolso(reserva_id, motivo)
    except PagoNoEncontrado:
        raise HTTPException(status_code=404, detail="No hay un pago exitoso para esa reserva")
    except ReembolsoNoAplicable:
        raise HTTPException(status_code=422, detail="La política de la tarifa no permite reembolso")
    return reembolso


@router.post("/reservas/{reserva_id}/diferencia-tarifa")
async def diferencia_tarifa_endpoint(reserva_id: str, monto_diferencia: float = Form(...)) -> dict:
    try:
        return await cobrar_o_reembolsar_diferencia(reserva_id, monto_diferencia)
    except PagoOriginalNoEncontrado:
        raise HTTPException(status_code=404, detail="No hay un pago exitoso para esa reserva")
    except CobroDiferenciaRechazado as exc:
        raise HTTPException(status_code=402, detail=exc.motivo)
