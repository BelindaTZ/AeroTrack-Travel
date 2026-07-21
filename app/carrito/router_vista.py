"""Vista HTML del carrito (RF-CAR-001,002,003,004) — capa de presentación
sobre el mismo `carrito_service.py` que ya usa `router_carrito.py`/
`router_checkout.py` (JSON). No reemplaza esos endpoints (los consumen tests
y clientes API existentes); agrega el camino navegable en el browser que
faltaba para que un pasajero pueda de verdad ver/confirmar su carrito.

**Alcance deliberado:** la confirmación de compra NO redirige a
`/reservas/{id}` — esa página (`construir_detalle` en
`router_reservas.py`) todavía asume una reserva de un solo vuelo
(`vuelo_id`/`tarifa_id` obligatorios en su schema) y no soporta reservas
multi-producto creadas aquí (`reserva_items` sin `vuelo_id`). Se muestra
una confirmación propia con los datos que Carrito ya tiene, sin tocar
Reservas — ver `errores-conocidos.md`."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.carrito.services.carrito_service import (
    CarritoVacio,
    CupoInsuficiente,
    ItemNoEncontrado,
    SinPermiso,
    TipoProductoInvalido,
    agregar_item,
    confirmar_checkout,
    eliminar_item,
    revalidar_precios,
    ver_carrito,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.session_service import verificar_sesion
from app.shared.descripcion_producto import describir_item
from app.shared.templating import templates

router = APIRouter(prefix="/carrito")


async def _pasajero_id(usuario: dict) -> str:
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    return pasajero["id"] if pasajero else None


@router.get("/ver")
async def ver(request: Request, usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    if pasajero_id is None:
        return templates.TemplateResponse(request, "carrito_ver.html", {"items": [], "total": 0.0, "cambios": [], "usuario": usuario})

    resultado = await ver_carrito(pasajero_id)
    cambios = (await revalidar_precios(pasajero_id))["cambios"] if resultado["items"] else []
    cambios_por_item = {c["item_id"]: c for c in cambios}

    items = []
    for item in resultado["items"]:
        etiqueta = await describir_item(item)
        items.append({**item, **etiqueta, "cambio": cambios_por_item.get(item["id"])})

    return templates.TemplateResponse(
        request,
        "carrito_ver.html",
        {"items": items, "total": resultado["total"], "tiene_carrito": resultado["carrito"] is not None, "usuario": usuario},
    )


@router.post("/agregar")
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
):
    pasajero_id = await _pasajero_id(usuario)
    if pasajero_id is None:
        return RedirectResponse("/vuelos/buscar?mensaje=Solo cuentas de pasajero tienen carrito", status_code=303)

    ids = {
        "vuelo_id": vuelo_id, "tarifa_vuelo_id": tarifa_vuelo_id,
        "hotel_id": hotel_id, "hotel_tarifa_id": hotel_tarifa_id,
        "auto_id": auto_id,
        "actividad_id": actividad_id, "actividad_horario_id": actividad_horario_id,
        "crucero_id": crucero_id, "crucero_camarote_id": crucero_camarote_id,
    }
    ids = {k: v for k, v in ids.items() if v}

    try:
        item = await agregar_item(pasajero_id, tipo_producto, ids, precio_snapshot, cantidad)
    except TipoProductoInvalido:
        return RedirectResponse("/carrito/ver?mensaje=Producto inválido", status_code=303)

    await AuditService().insertar("agregar_item", "carrito_items", usuario_id=usuario["id"], registro_id=item["id"])
    return RedirectResponse("/carrito/ver?mensaje=Agregado al carrito", status_code=303)


@router.post("/eliminar/{item_id}")
async def eliminar(item_id: str, usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    try:
        await eliminar_item(pasajero_id, item_id)
    except (ItemNoEncontrado, SinPermiso):
        return RedirectResponse("/carrito/ver?mensaje=No se pudo eliminar el ítem", status_code=303)

    await AuditService().insertar("eliminar_item", "carrito_items", usuario_id=usuario["id"], registro_id=item_id)
    return RedirectResponse("/carrito/ver?mensaje=Ítem eliminado", status_code=303)


@router.post("/confirmar")
async def confirmar(request: Request, usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    try:
        reserva = await confirmar_checkout(pasajero_id)
    except CarritoVacio:
        return RedirectResponse("/carrito/ver?mensaje=El carrito está vacío", status_code=303)
    except CupoInsuficiente:
        return RedirectResponse(
            "/carrito/ver?mensaje=Uno o más ítems ya no tienen cupo disponible — revisa tu carrito", status_code=303
        )

    await AuditService().insertar(
        "checkout_carrito", "reservas", usuario_id=usuario["id"], registro_id=reserva["id"],
        detalle={"codigo_reserva": reserva["codigo_reserva"], "es_paquete": reserva["es_paquete"]},
    )
    return templates.TemplateResponse(request, "carrito_confirmacion.html", {"reserva": reserva, "usuario": usuario})
