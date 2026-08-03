"""RF-PAQ-001,003,005 (CU-O76,O78,O80) — construir paquete, cambiar
componente, agregar traslado aeropuerto.

**Alcance de esta ronda:** mismo criterio que Carrito — acepta IDs directos
de producto (Vuelos/Hoteles/Autos/Actividades no tienen todas su pantalla
de selección real todavía), no una construcción guiada paso a paso."""

from fastapi import APIRouter, Depends, Form, HTTPException

from app.paquetes.services.paquete_service import (
    CupoNoDisponible,
    ReservaNoEncontrada,
    SinPermiso,
    agregar_componente,
    agregar_traslado_aeropuerto,
    cambiar_componente,
    iniciar_paquete,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.session_service import verificar_sesion

router = APIRouter(prefix="/paquetes")


async def _pasajero_id(usuario: dict) -> str:
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise HTTPException(status_code=400, detail="Solo cuentas de pasajero pueden construir un paquete")
    return pasajero["id"]


@router.post("/iniciar")
async def iniciar(
    vuelo_id: str = Form(...),
    tarifa_vuelo_id: str = Form(...),
    precio_final: float = Form(...),
    usuario: dict = Depends(verificar_sesion),
) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    try:
        reserva = await iniciar_paquete(pasajero_id, vuelo_id, tarifa_vuelo_id, precio_final)
    except CupoNoDisponible:
        raise HTTPException(status_code=409, detail="Esa tarifa ya no tiene cupo disponible")
    await AuditService().insertar("iniciar_paquete", "reservas", usuario_id=usuario["id"], registro_id=reserva["id"])
    return reserva


@router.post("/{reserva_id}/agregar-componente")
async def agregar(
    reserva_id: str,
    tipo_producto: str = Form(...),
    precio_final: float = Form(...),
    hotel_id: str | None = Form(None),
    hotel_tarifa_id: str | None = Form(None),
    auto_id: str | None = Form(None),
    actividad_id: str | None = Form(None),
    actividad_horario_id: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    ids = {
        "hotel_id": hotel_id,
        "hotel_tarifa_id": hotel_tarifa_id,
        "auto_id": auto_id,
        "actividad_id": actividad_id,
        "actividad_horario_id": actividad_horario_id,
    }
    ids = {k: v for k, v in ids.items() if v}

    try:
        item = await agregar_componente(pasajero_id, reserva_id, tipo_producto, ids, precio_final)
    except ReservaNoEncontrada:
        raise HTTPException(status_code=404, detail="Paquete no encontrado")
    except SinPermiso:
        raise HTTPException(status_code=403, detail="Sin permiso sobre ese paquete")
    except CupoNoDisponible:
        raise HTTPException(status_code=409, detail="Ese producto ya no tiene cupo disponible")

    await AuditService().insertar("agregar_componente", "reserva_items", usuario_id=usuario["id"], registro_id=item["id"])
    return item


@router.put("/{reserva_id}/componente/{item_id}")
async def cambiar(
    reserva_id: str,
    item_id: str,
    precio_final: float = Form(...),
    hotel_id: str | None = Form(None),
    hotel_tarifa_id: str | None = Form(None),
    auto_id: str | None = Form(None),
    actividad_id: str | None = Form(None),
    actividad_horario_id: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    nuevos_ids = {
        "hotel_id": hotel_id,
        "hotel_tarifa_id": hotel_tarifa_id,
        "auto_id": auto_id,
        "actividad_id": actividad_id,
        "actividad_horario_id": actividad_horario_id,
    }
    nuevos_ids = {k: v for k, v in nuevos_ids.items() if v}

    try:
        item = await cambiar_componente(pasajero_id, reserva_id, item_id, nuevos_ids, precio_final)
    except ReservaNoEncontrada:
        raise HTTPException(status_code=404, detail="Paquete no encontrado")
    except SinPermiso:
        raise HTTPException(status_code=403, detail="Sin permiso sobre ese paquete")
    except CupoNoDisponible:
        raise HTTPException(status_code=409, detail="Ese producto ya no tiene cupo disponible")

    await AuditService().insertar("cambiar_componente", "reserva_items", usuario_id=usuario["id"], registro_id=item["id"])
    return item


@router.post("/{reserva_id}/traslado-aeropuerto")
async def traslado(
    reserva_id: str,
    descripcion: str = Form(...),
    precio: float = Form(...),
    usuario: dict = Depends(verificar_sesion),
) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    try:
        extra = await agregar_traslado_aeropuerto(pasajero_id, reserva_id, descripcion, precio)
    except ReservaNoEncontrada:
        raise HTTPException(status_code=404, detail="Paquete no encontrado")
    except SinPermiso:
        raise HTTPException(status_code=403, detail="Sin permiso sobre ese paquete")

    await AuditService().insertar("agregar_traslado", "reserva_extras", usuario_id=usuario["id"], registro_id=extra["id"])
    return extra
