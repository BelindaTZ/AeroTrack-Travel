"""RF-RES-001,005 — checkout, confirmación y consulta de reserva propia."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.schemas import ExtraOut, ReservaDetalleOut
from app.reservas.services.cancelar_reserva_service import (
    ReservaNoEncontrada as ReservaNoEncontradaCancelar,
)
from app.reservas.services.cancelar_reserva_service import (
    SinPermiso as SinPermisoCancelar,
)
from app.reservas.services.cancelar_reserva_service import VueloYaCompletado, cancelar_reserva
from app.reservas.services.crear_reserva_service import (
    CupoNoDisponible,
    PasajeroNoEncontrado,
    PrecioDesactualizado,
    TarifaNoEncontrada,
    crear_reserva,
)
from app.reservas.services.modificar_reserva_service import (
    CupoNoDisponible as CupoNoDisponibleModificar,
)
from app.reservas.services.modificar_reserva_service import (
    ReservaBloqueada,
    modificar_reserva,
)
from app.reservas.services.modificar_reserva_service import (
    ReservaNoEncontrada as ReservaNoEncontradaModificar,
)
from app.reservas.services.modificar_reserva_service import (
    SinPermiso as SinPermisoModificar,
)
from app.reservas.services.modificar_reserva_service import (
    TarifaNoEncontrada as TarifaNoEncontradaModificar,
)
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates
from app.vuelos.repositories.dims_reader import resolver_aeropuerto
from app.vuelos.repositories.vuelos_repo import VuelosRepository

router = APIRouter(prefix="/reservas")

EXTRAS_DISPONIBLES = [
    {"tipo": "equipaje", "descripcion": "Equipaje facturado adicional", "precio": 35.0},
    {"tipo": "asiento", "descripcion": "Selección de asiento preferente", "precio": 15.0},
    {"tipo": "seguro", "descripcion": "Seguro de viaje", "precio": 20.0},
]


async def construir_detalle(reserva: dict) -> ReservaDetalleOut:
    vuelos_repo = VuelosRepository()
    reservas_repo = ReservasRepository()

    vuelo = await vuelos_repo.obtener_vuelo(reserva["vuelo_id"])
    tarifa = await vuelos_repo.obtener_tarifa(reserva["tarifa_id"])
    aerolinea = await vuelos_repo.obtener_aerolinea(vuelo["aerolinea_id"])
    nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
    extras = await reservas_repo.extras_de_reserva(reserva["id"])

    return ReservaDetalleOut(
        id=reserva["id"],
        codigo_reserva=reserva["codigo_reserva"],
        estado=reserva["estado"],
        canal=reserva["canal"],
        total_pagar=reserva["total_pagar"],
        fecha_reserva=reserva["fecha_reserva"],
        fecha_expiracion_pago=reserva.get("fecha_expiracion_pago"),
        numero_vuelo=vuelo["numero_vuelo"],
        aerolinea_nombre=aerolinea["nombre"],
        origen_legible=await resolver_aeropuerto(vuelo["origen_codigo"]),
        destino_legible=await resolver_aeropuerto(vuelo["destino_codigo"]),
        fecha_salida=vuelo["fecha_salida"][:10],
        hora_salida_programada=vuelo["hora_salida_programada"],
        nivel_tarifa=nivel["nombre"],
        precio_tarifa=tarifa["precio_final"],
        extras=[
            ExtraOut(tipo=e["tipo"], descripcion=e.get("descripcion"), precio=e["precio"])
            for e in extras
        ],
    )


async def _contexto_checkout(usuario: dict, tarifa_id: str, **extra) -> dict | None:
    vuelos_repo = VuelosRepository()
    tarifa = await vuelos_repo.obtener_tarifa(tarifa_id)
    if tarifa is None:
        return None
    vuelo = await vuelos_repo.obtener_vuelo(tarifa["vuelo_id"])
    aerolinea = await vuelos_repo.obtener_aerolinea(vuelo["aerolinea_id"])
    nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
    contexto = {
        "usuario": usuario,
        "tarifa": tarifa,
        "vuelo": vuelo,
        "aerolinea": aerolinea,
        "nivel": nivel,
        "origen_legible": await resolver_aeropuerto(vuelo["origen_codigo"]),
        "destino_legible": await resolver_aeropuerto(vuelo["destino_codigo"]),
        "extras_disponibles": EXTRAS_DISPONIBLES,
    }
    contexto.update(extra)
    return contexto


@router.get("/nueva")
async def nueva_form(request: Request, tarifa_id: str, usuario: dict = Depends(verificar_sesion)):
    contexto = await _contexto_checkout(usuario, tarifa_id)
    if contexto is None:
        return RedirectResponse("/vuelos/buscar", status_code=303)
    return templates.TemplateResponse(request, "checkout.html", contexto)


@router.post("")
async def crear(
    request: Request,
    tarifa_id: str = Form(...),
    precio_esperado: float = Form(...),
    extras: list[str] = Form([]),
    usuario: dict = Depends(verificar_sesion),
):
    extras_data = [e for e in EXTRAS_DISPONIBLES if e["tipo"] in extras]

    try:
        reserva = await crear_reserva(usuario, tarifa_id, precio_esperado, extras_data)
    except PasajeroNoEncontrado:
        contexto = await _contexto_checkout(
            usuario, tarifa_id, error="Solo cuentas de pasajero pueden reservar por autoservicio."
        )
        return templates.TemplateResponse(request, "checkout.html", contexto, status_code=400)
    except TarifaNoEncontrada:
        return RedirectResponse("/vuelos/buscar", status_code=303)
    except PrecioDesactualizado as exc:
        contexto = await _contexto_checkout(
            usuario,
            tarifa_id,
            error=f"El precio cambió a ${exc.precio_actual:.2f}. Revisa y confirma de nuevo.",
        )
        return templates.TemplateResponse(request, "checkout.html", contexto, status_code=409)
    except CupoNoDisponible:
        contexto = await _contexto_checkout(
            usuario, tarifa_id, error="Ese vuelo ya no tiene cupo disponible en este nivel de tarifa."
        )
        return templates.TemplateResponse(request, "checkout.html", contexto, status_code=409)

    await AuditService().insertar(
        "crear",
        "reservas",
        usuario_id=usuario["id"],
        registro_id=reserva["id"],
        detalle={"canal": "autoservicio", "codigo_reserva": reserva["codigo_reserva"]},
    )
    return RedirectResponse(f"/reservas/{reserva['id']}", status_code=303)


@router.get("")
async def mis_reservas(request: Request, usuario: dict = Depends(verificar_sesion)):
    repo = ReservasRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    reservas = []
    if pasajero is not None:
        crudas = await repo.listar_reservas_de_pasajero(pasajero["id"])
        reservas = [await construir_detalle(r) for r in crudas]
    return templates.TemplateResponse(
        request, "mis_reservas.html", {"usuario": usuario, "reservas": reservas}
    )


@router.get("/{reserva_id}")
async def detalle(request: Request, reserva_id: str, usuario: dict = Depends(verificar_sesion)):
    repo = ReservasRepository()
    reserva = await repo.obtener_reserva(reserva_id)
    if reserva is None:
        return templates.TemplateResponse(
            request, "detalle_reserva.html", {"usuario": usuario, "reserva": None}, status_code=404
        )

    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    es_titular = pasajero is not None and reserva["pasajero_titular_id"] == pasajero["id"]
    es_agente_de_la_reserva = reserva.get("agente_id") == usuario["id"]
    if not (es_titular or es_agente_de_la_reserva or usuario.get("tipo_actor") == "administrador"):
        return templates.TemplateResponse(
            request, "detalle_reserva.html", {"usuario": usuario, "reserva": None}, status_code=404
        )

    detalle_reserva = await construir_detalle(reserva)
    return templates.TemplateResponse(
        request, "detalle_reserva.html", {"usuario": usuario, "reserva": detalle_reserva}
    )


@router.post("/{reserva_id}/cancelar")
async def cancelar(reserva_id: str, usuario: dict = Depends(verificar_sesion)):
    try:
        await cancelar_reserva(usuario, reserva_id)
    except ReservaNoEncontradaCancelar:
        return RedirectResponse("/reservas?mensaje=Reserva no encontrada", status_code=303)
    except SinPermisoCancelar:
        return RedirectResponse("/reservas?mensaje=Sin permiso sobre esa reserva", status_code=303)
    except VueloYaCompletado:
        return RedirectResponse(
            f"/reservas/{reserva_id}?mensaje=No es posible cancelar un vuelo ya realizado.",
            status_code=303,
        )
    return RedirectResponse(f"/reservas/{reserva_id}?mensaje=Reserva cancelada", status_code=303)


@router.put("/{reserva_id}")
async def modificar(
    reserva_id: str,
    nueva_tarifa_id: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
):
    try:
        actualizada = await modificar_reserva(usuario, reserva_id, nueva_tarifa_id)
    except ReservaNoEncontradaModificar:
        return JSONResponse(status_code=404, content={"detail": "Reserva no encontrada"})
    except SinPermisoModificar:
        return JSONResponse(status_code=403, content={"detail": "Sin permiso sobre esa reserva"})
    except ReservaBloqueada:
        return JSONResponse(
            status_code=409, content={"detail": "No se puede modificar una reserva cancelada o completada"}
        )
    except TarifaNoEncontradaModificar:
        return JSONResponse(status_code=404, content={"detail": "Tarifa nueva no encontrada"})
    except CupoNoDisponibleModificar:
        return JSONResponse(status_code=409, content={"detail": "Sin cupo disponible en la nueva tarifa"})
    return JSONResponse(
        {"id": actualizada["id"], "estado": actualizada["estado"], "total_pagar": actualizada["total_pagar"]}
    )
