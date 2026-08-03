"""RF-PAQ-002,004 (CU-O77,O79) — resumen con desglose de ahorro y
condiciones por componente; confirmar paquete (RN-PAQ-001/002)."""

from fastapi import APIRouter, Depends, HTTPException

from app.paquetes.services.paquete_service import (
    ComponenteObligatorioFaltante,
    ReservaNoEncontrada,
    SinPermiso,
    calcular_resumen,
    condiciones_por_componente,
    confirmar_paquete,
    verificar_propiedad,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.session_service import verificar_sesion

router = APIRouter(prefix="/paquetes")


async def _pasajero_id(usuario: dict) -> str:
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise HTTPException(status_code=400, detail="Solo cuentas de pasajero pueden ver un paquete")
    return pasajero["id"]


@router.get("/{reserva_id}/resumen")
async def resumen(reserva_id: str, usuario: dict = Depends(verificar_sesion)) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    # Antes solo verificaba que el usuario FUERA pasajero, nunca que esta
    # reserva fuera SUYA — cualquier pasajero autenticado podía ver el
    # resumen/condiciones de un paquete ajeno adivinando el reserva_id (IDOR).
    try:
        await verificar_propiedad(ReservasRepository(), pasajero_id, reserva_id)
    except ReservaNoEncontrada:
        raise HTTPException(status_code=404, detail="Paquete no encontrado")
    except SinPermiso:
        raise HTTPException(status_code=403, detail="Sin permiso sobre ese paquete")

    desglose = await calcular_resumen(reserva_id)
    desglose["condiciones"] = await condiciones_por_componente(reserva_id)
    return desglose


@router.post("/{reserva_id}/confirmar")
async def confirmar(reserva_id: str, usuario: dict = Depends(verificar_sesion)) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    try:
        reserva = await confirmar_paquete(pasajero_id, reserva_id)
    except ReservaNoEncontrada:
        raise HTTPException(status_code=404, detail="Paquete no encontrado")
    except SinPermiso:
        raise HTTPException(status_code=403, detail="Sin permiso sobre ese paquete")
    except ComponenteObligatorioFaltante as exc:
        raise HTTPException(status_code=409, detail=f"Faltan componentes obligatorios: {', '.join(sorted(exc.faltantes))}")

    await AuditService().insertar(
        "confirmar_paquete",
        "reservas",
        usuario_id=usuario["id"],
        registro_id=reserva["id"],
        detalle={"descuento_paquete_pct": reserva["descuento_paquete_pct"], "total_pagar": reserva["total_pagar"]},
    )
    return reserva
