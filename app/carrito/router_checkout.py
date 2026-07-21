"""RF-CAR-004 (CU-O96) — checkout desde el carrito, con revalidación de
precio (RN-CAR-001) antes de confirmar (REG-G2)."""

from fastapi import APIRouter, Depends, HTTPException

from app.carrito.services.carrito_service import CarritoVacio, CupoInsuficiente, confirmar_checkout, revalidar_precios
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.session_service import verificar_sesion

router = APIRouter(prefix="/carrito/checkout")


async def _pasajero_id(usuario: dict) -> str:
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise HTTPException(status_code=400, detail="Solo cuentas de pasajero tienen carrito")
    return pasajero["id"]


@router.get("/revalidar")
async def revalidar(usuario: dict = Depends(verificar_sesion)) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    return await revalidar_precios(pasajero_id)


@router.post("/confirmar")
async def confirmar(usuario: dict = Depends(verificar_sesion)) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    try:
        reserva = await confirmar_checkout(pasajero_id)
    except CarritoVacio:
        raise HTTPException(status_code=409, detail="El carrito está vacío — RN-CAR-003")
    except CupoInsuficiente as exc:
        raise HTTPException(status_code=409, detail={"error": "cupo_insuficiente", "item_ids": exc.item_ids})

    await AuditService().insertar(
        "checkout_carrito",
        "reservas",
        usuario_id=usuario["id"],
        registro_id=reserva["id"],
        detalle={"codigo_reserva": reserva["codigo_reserva"], "es_paquete": reserva["es_paquete"]},
    )
    return reserva
