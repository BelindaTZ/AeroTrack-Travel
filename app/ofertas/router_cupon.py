"""RF-OFE-003 (CU-O103) — aplicar cupón de descuento sobre una reserva
propia en `pendiente_pago`, `<<extend>>` del checkout de Carrito/Reservas."""

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse

from app.ofertas.services.ofertas_service import CuponInvalido, aplicar_cupon
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import verificar_sesion

router = APIRouter()


@router.post("/checkout/aplicar-cupon")
async def checkout_aplicar_cupon(
    reserva_id: str = Form(...),
    codigo: str = Form(...),
    next: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
):
    destino = next or f"/reservas/{reserva_id}"
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        return RedirectResponse(f"{destino}?mensaje=Solo cuentas de pasajero pueden aplicar cupones", status_code=303)

    try:
        resultado = await aplicar_cupon(usuario, pasajero["id"], reserva_id, codigo)
    except CuponInvalido as exc:
        return RedirectResponse(f"{destino}?mensaje={exc.motivo}", status_code=303)

    return RedirectResponse(
        f"{destino}?mensaje=Cupón aplicado — descuento de ${resultado['monto_descontado']:.2f}", status_code=303
    )
