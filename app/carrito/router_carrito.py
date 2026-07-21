"""RF-CAR-001,002,003 (CU-O93,O94,O95) — ver, agregar y eliminar ítems del
carrito.

**Alcance de esta ronda:** los 5 módulos de catálogo (Vuelos/Hoteles/Autos/
Actividades/Cruceros) todavía no tienen su propia pantalla de selección
para el pasajero (solo Vuelos) — este router acepta directamente los IDs
del producto elegido en el body, en vez de integrarse con una pantalla de
"agregar al carrito" que no existe todavía en las otras 4 verticales. Se
completa cuando cada módulo tenga su Fase 2/3 (búsqueda/selección real)."""

from fastapi import APIRouter, Depends, Form, HTTPException

from app.carrito.services.carrito_service import (
    ItemNoEncontrado,
    SinPermiso,
    TipoProductoInvalido,
    agregar_item,
    eliminar_item,
    ver_carrito,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.session_service import verificar_sesion

router = APIRouter(prefix="/carrito")


async def _pasajero_id(usuario: dict) -> str:
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise HTTPException(status_code=400, detail="Solo cuentas de pasajero tienen carrito")
    return pasajero["id"]


@router.get("")
async def ver(usuario: dict = Depends(verificar_sesion)) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    return await ver_carrito(pasajero_id)


@router.post("/items")
async def agregar(
    tipo_producto: str = Form(...),
    precio_snapshot: float = Form(...),
    cantidad: int = Form(1),
    vuelo_id: str | None = Form(None),
    tarifa_vuelo_id: str | None = Form(None),
    hotel_id: str | None = Form(None),
    hotel_tarifa_id: str | None = Form(None),
    auto_id: str | None = Form(None),
    actividad_id: str | None = Form(None),
    actividad_horario_id: str | None = Form(None),
    crucero_id: str | None = Form(None),
    crucero_camarote_id: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    ids = {
        "vuelo_id": vuelo_id,
        "tarifa_vuelo_id": tarifa_vuelo_id,
        "hotel_id": hotel_id,
        "hotel_tarifa_id": hotel_tarifa_id,
        "auto_id": auto_id,
        "actividad_id": actividad_id,
        "actividad_horario_id": actividad_horario_id,
        "crucero_id": crucero_id,
        "crucero_camarote_id": crucero_camarote_id,
    }
    ids = {k: v for k, v in ids.items() if v}

    try:
        item = await agregar_item(pasajero_id, tipo_producto, ids, precio_snapshot, cantidad)
    except TipoProductoInvalido:
        raise HTTPException(status_code=422, detail="tipo_producto inválido")

    await AuditService().insertar(
        "agregar_item", "carrito_items", usuario_id=usuario["id"], registro_id=item["id"]
    )
    return item


@router.delete("/items/{item_id}")
async def eliminar(item_id: str, usuario: dict = Depends(verificar_sesion)) -> dict:
    pasajero_id = await _pasajero_id(usuario)
    try:
        await eliminar_item(pasajero_id, item_id)
    except ItemNoEncontrado:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")
    except SinPermiso:
        raise HTTPException(status_code=403, detail="Sin permiso sobre ese ítem")

    await AuditService().insertar("eliminar_item", "carrito_items", usuario_id=usuario["id"], registro_id=item_id)
    return {"eliminado": True}
