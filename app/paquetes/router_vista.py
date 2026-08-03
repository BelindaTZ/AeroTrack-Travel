"""Vista HTML de Paquetes (RF-PAQ-001-005) — sección exclusiva para que un
pasajero con intención de ahorrar vea qué combinaciones de descuento existen
y arme su paquete paso a paso (vuelo -> hotel -> auto/actividad opcionales),
capa de presentación sobre `paquete_service.py` (ya usado por
`router_construccion.py`/`router_resumen.py`, JSON puro) — mismo patrón que
`app/carrito/router_vista.py` sobre `carrito_service.py`: no reemplaza esos
endpoints, agrega el camino navegable en el browser que faltaba.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.paquetes.repositories.paquetes_repo import PaquetesRepository
from app.paquetes.services.paquete_service import (
    ComponenteObligatorioFaltante,
    CupoNoDisponible,
    ReservaNoEncontrada,
    SinPermiso,
    agregar_componente,
    agregar_traslado_aeropuerto,
    calcular_resumen,
    condiciones_por_componente,
    confirmar_paquete,
    iniciar_paquete,
    verificar_propiedad,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.session_service import usuario_opcional, verificar_sesion
from app.shared.descripcion_producto import describir_item
from app.shared.templating import templates

router = APIRouter(prefix="/paquetes")


async def _pasajero_id(usuario: dict) -> str | None:
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    return pasajero["id"] if pasajero else None


@router.get("")
async def inicio(request: Request, usuario: dict | None = Depends(usuario_opcional)):
    combinaciones = await PaquetesRepository().listar_combinaciones_activas()
    return templates.TemplateResponse(
        request, "paquetes_inicio.html", {"combinaciones": combinaciones, "usuario": usuario}
    )


@router.post("/nuevo")
async def nuevo(
    vuelo_id: str = Form(...),
    tarifa_vuelo_id: str = Form(...),
    precio_final: float = Form(...),
    usuario: dict = Depends(verificar_sesion),
):
    pasajero_id = await _pasajero_id(usuario)
    if pasajero_id is None:
        return RedirectResponse(
            "/vuelos/buscar?mensaje=Solo cuentas de pasajero pueden armar un paquete", status_code=303
        )
    try:
        reserva = await iniciar_paquete(pasajero_id, vuelo_id, tarifa_vuelo_id, precio_final)
    except CupoNoDisponible:
        return RedirectResponse(
            f"/vuelos/{vuelo_id}?mensaje=Esa tarifa ya no tiene cupo disponible", status_code=303
        )
    await AuditService().insertar("iniciar_paquete", "reservas", usuario_id=usuario["id"], registro_id=reserva["id"])
    return RedirectResponse(f"/paquetes/{reserva['id']}/armar", status_code=303)


@router.get("/{reserva_id}/armar")
async def armar(request: Request, reserva_id: str, usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    reservas_repo = ReservasRepository()
    if pasajero_id is None:
        return RedirectResponse("/paquetes", status_code=303)

    try:
        reserva = await verificar_propiedad(reservas_repo, pasajero_id, reserva_id)
    except (ReservaNoEncontrada, SinPermiso):
        return RedirectResponse("/paquetes?mensaje=Paquete no encontrado", status_code=303)

    if reserva["estado"] != "pendiente_pago":
        # Ya confirmado (o cancelado/expirado) — nada que seguir armando,
        # su ficha real vive en /reservas/{id} de ahora en más.
        return RedirectResponse(f"/reservas/{reserva_id}", status_code=303)

    items = await reservas_repo.items_de_reserva(reserva_id)
    resumen = await calcular_resumen(reserva_id)
    condiciones = {c["tipo_producto"]: c["condiciones"] for c in await condiciones_por_componente(reserva_id)}
    tipos_presentes = {i["tipo_producto"] for i in items}

    items_vista = []
    for item in items:
        etiqueta = await describir_item(item)
        items_vista.append({**item, **etiqueta, "condiciones": condiciones.get(item["tipo_producto"])})

    return templates.TemplateResponse(
        request,
        "paquetes_armar.html",
        {
            "reserva": reserva,
            "resumen": resumen,
            "items": items_vista,
            "tipos_presentes": tipos_presentes,
            "usuario": usuario,
        },
    )


@router.post("/{reserva_id}/agregar")
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
):
    pasajero_id = await _pasajero_id(usuario)
    if pasajero_id is None:
        return RedirectResponse("/paquetes", status_code=303)

    ids = {
        "hotel_id": hotel_id, "hotel_tarifa_id": hotel_tarifa_id,
        "auto_id": auto_id,
        "actividad_id": actividad_id, "actividad_horario_id": actividad_horario_id,
    }
    ids = {k: v for k, v in ids.items() if v}

    try:
        item = await agregar_componente(pasajero_id, reserva_id, tipo_producto, ids, precio_final)
    except (ReservaNoEncontrada, SinPermiso):
        return RedirectResponse("/paquetes?mensaje=Paquete no encontrado", status_code=303)
    except CupoNoDisponible:
        return RedirectResponse(
            f"/paquetes/{reserva_id}/armar?mensaje=Ese producto ya no tiene cupo disponible", status_code=303
        )

    await AuditService().insertar("agregar_componente", "reserva_items", usuario_id=usuario["id"], registro_id=item["id"])
    return RedirectResponse(f"/paquetes/{reserva_id}/armar?mensaje=Agregado a tu paquete", status_code=303)


@router.post("/{reserva_id}/traslado")
async def traslado(
    reserva_id: str,
    descripcion: str = Form(...),
    precio: float = Form(...),
    usuario: dict = Depends(verificar_sesion),
):
    pasajero_id = await _pasajero_id(usuario)
    if pasajero_id is None:
        return RedirectResponse("/paquetes", status_code=303)

    try:
        extra = await agregar_traslado_aeropuerto(pasajero_id, reserva_id, descripcion, precio)
    except (ReservaNoEncontrada, SinPermiso):
        return RedirectResponse("/paquetes?mensaje=Paquete no encontrado", status_code=303)

    await AuditService().insertar("agregar_traslado", "reserva_extras", usuario_id=usuario["id"], registro_id=extra["id"])
    return RedirectResponse(f"/paquetes/{reserva_id}/armar?mensaje=Traslado agregado", status_code=303)


@router.post("/{reserva_id}/finalizar")
async def finalizar(reserva_id: str, usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    if pasajero_id is None:
        return RedirectResponse("/paquetes", status_code=303)

    try:
        reserva = await confirmar_paquete(pasajero_id, reserva_id)
    except (ReservaNoEncontrada, SinPermiso):
        return RedirectResponse("/paquetes?mensaje=Paquete no encontrado", status_code=303)
    except ComponenteObligatorioFaltante as exc:
        faltantes = ", ".join(sorted(exc.faltantes))
        return RedirectResponse(
            f"/paquetes/{reserva_id}/armar?mensaje=Falta agregar: {faltantes}", status_code=303
        )

    await AuditService().insertar(
        "confirmar_paquete",
        "reservas",
        usuario_id=usuario["id"],
        registro_id=reserva["id"],
        detalle={"descuento_paquete_pct": reserva["descuento_paquete_pct"], "total_pagar": reserva["total_pagar"]},
    )
    return RedirectResponse(f"/reservas/{reserva_id}?mensaje=Paquete confirmado", status_code=303)
