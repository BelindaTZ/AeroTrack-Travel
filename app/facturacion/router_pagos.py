"""RF-FAC-001,008 — pagar una reserva pendiente_pago; historial propio (Fase 3)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.services.pago_service import (
    PagoRechazadoPorStripe,
    ReservaNoEncontrada,
    ReservaNoPagable,
    SinPermiso,
    procesar_pago,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates
from app.vuelos.repositories.vuelos_repo import VuelosRepository

router = APIRouter()


@router.get("/reservas/{reserva_id}/pagar")
async def pagar_form(request: Request, reserva_id: str, usuario: dict = Depends(verificar_sesion)):
    repo = ReservasRepository()
    reserva = await repo.obtener_reserva(reserva_id)
    if reserva is None:
        return RedirectResponse("/reservas", status_code=303)
    return templates.TemplateResponse(
        request, "checkout_pago.html", {"usuario": usuario, "reserva": reserva}
    )


@router.post("/reservas/{reserva_id}/pagar")
async def pagar_submit(
    request: Request,
    reserva_id: str,
    escenario: str = Form("exitoso"),
    usuario: dict = Depends(verificar_sesion),
):
    try:
        await procesar_pago(usuario, reserva_id, escenario)
    except ReservaNoEncontrada:
        return RedirectResponse("/reservas", status_code=303)
    except SinPermiso:
        return RedirectResponse("/reservas?mensaje=Sin permiso sobre esa reserva", status_code=303)
    except ReservaNoPagable:
        return RedirectResponse(
            f"/reservas/{reserva_id}?mensaje=Esta reserva ya no está pendiente de pago", status_code=303
        )
    except PagoRechazadoPorStripe as exc:
        repo = ReservasRepository()
        reserva = await repo.obtener_reserva(reserva_id)
        return templates.TemplateResponse(
            request,
            "checkout_pago.html",
            {"usuario": usuario, "reserva": reserva, "error": exc.motivo},
            status_code=402,
        )

    return RedirectResponse(f"/reservas/{reserva_id}?mensaje=Pago exitoso", status_code=303)


@router.get("/pagos")
async def historial(request: Request, usuario: dict = Depends(verificar_sesion)):
    reservas_repo = ReservasRepository()
    facturacion_repo = FacturacionRepository()
    vuelos_repo = VuelosRepository()

    pasajero = await reservas_repo.pasajero_de_usuario(usuario["id"])
    pagos_out = []
    if pasajero is not None:
        reservas = await reservas_repo.listar_reservas_de_pasajero(pasajero["id"])
        for reserva in reservas:
            for pago in await facturacion_repo.pagos_de_reserva(reserva["id"]):
                vuelo = await vuelos_repo.obtener_vuelo(reserva["vuelo_id"])
                factura = await facturacion_repo.factura_de_pago(pago["id"])
                pagos_out.append(
                    {
                        "pago": pago,
                        "codigo_reserva": reserva["codigo_reserva"],
                        "numero_vuelo": vuelo["numero_vuelo"] if vuelo else "",
                        "reserva_id": reserva["id"],
                        "factura_id": factura["id"] if factura else None,
                    }
                )
    pagos_out.sort(key=lambda p: p["pago"].get("created", ""), reverse=True)
    return templates.TemplateResponse(
        request, "historial_pagos.html", {"usuario": usuario, "pagos": pagos_out}
    )
