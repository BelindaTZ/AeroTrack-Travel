"""RF-RES-001,005 — checkout, confirmación y consulta de reserva propia."""

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.schemas import ExtraOut, ItemReservaOut, ReservaDetalleOut
from app.shared.descripcion_producto import describir_item
from app.reservas.services.cancelar_reserva_service import (
    ReservaNoEncontrada as ReservaNoEncontradaCancelar,
)
from app.reservas.services.cancelar_reserva_service import (
    SinPermiso as SinPermisoCancelar,
)
from app.reservas.services.cancelar_reserva_service import VueloYaCompletado, cancelar_reserva
from app.reservas.services.crear_reserva_service import (
    AsientoNoDisponible,
    AsientoNoValido,
    CupoNoDisponible,
    PasajeroNoEncontrado,
    PrecioDesactualizado,
    SeleccionNoPermitidaAun,
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
from app.shared.flash import redirect_con_mensaje
from app.reservas.services.modificar_reserva_service import (
    TarifaNoEncontrada as TarifaNoEncontradaModificar,
)
import datetime

from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import tiene_permiso
from app.seguridad.services.session_service import verificar_sesion
from app.shared.nav import nav_context
from app.shared.templating import templates
from app.vuelos.repositories.dims_reader import resolver_aeropuerto
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.asientos_service import ventana_checkin_abierta

# WP-04 (auditoría de WorkPanels, 2026-07-31) — etiqueta del link de "volver"
# cuando se llega desde el panel de backoffice, ver detalle().
ETIQUETAS_VOLVER = {
    "/backoffice/reservas/reporte": "Reporte de reservas",
    "/backoffice/reservas/mi-cartera": "Mi cartera",
}

router = APIRouter(prefix="/reservas")

# "asiento" (cargo plano de $15) se retiró — reemplazado por selección real
# de un asiento concreto del mapa (RF-VUE-011/012, ver checkout.html), que
# ya cobra su propio recargo solo si el asiento elegido es premium.
_PRECIO_DEFAULT_EQUIPAJE = 35.0
_PRECIO_DEFAULT_SEGURO = 20.0


async def _extras_disponibles(repo: ReservasRepository) -> list[dict]:
    """WP-08 (ampliación de sesión 2026-08-01) — precio editable desde
    Configuración del sistema (`reservas.precio_extra_equipaje`/`_seguro`);
    tipo/descripción quedan fijos porque el checkout los usa como
    identificador, no como texto libre."""
    config_equipaje = await repo.config("reservas.precio_extra_equipaje")
    config_seguro = await repo.config("reservas.precio_extra_seguro")
    return [
        {
            "tipo": "equipaje", "descripcion": "Equipaje facturado adicional",
            "precio": float(config_equipaje["valor"]) if config_equipaje else _PRECIO_DEFAULT_EQUIPAJE,
        },
        {
            "tipo": "seguro", "descripcion": "Seguro de viaje",
            "precio": float(config_seguro["valor"]) if config_seguro else _PRECIO_DEFAULT_SEGURO,
        },
    ]


async def construir_detalle(reserva: dict) -> ReservaDetalleOut:
    vuelos_repo = VuelosRepository()
    reservas_repo = ReservasRepository()
    extras = await reservas_repo.extras_de_reserva(reserva["id"])
    extras_out = [
        ExtraOut(tipo=e["tipo"], descripcion=e.get("descripcion"), precio=e["precio"]) for e in extras
    ]

    if not reserva.get("vuelo_id"):
        # Reserva multi-producto (Carrito, 2026-07-19) — sin componente de
        # vuelo, se describe por sus reserva_items en vez del bloque de
        # vuelo de abajo (ver ReservaDetalleOut.es_multiproducto).
        items = await reservas_repo.items_de_reserva(reserva["id"])
        items_out = []
        for item in items:
            etiqueta = await describir_item(item)
            items_out.append(
                ItemReservaOut(
                    tipo_producto=item["tipo_producto"],
                    titulo=etiqueta["titulo"],
                    href=etiqueta["href"],
                    cantidad=item.get("cantidad") or 1,
                    precio_final=item["precio_final"],
                )
            )
        return ReservaDetalleOut(
            id=reserva["id"],
            codigo_reserva=reserva["codigo_reserva"],
            estado=reserva["estado"],
            canal=reserva["canal"],
            total_pagar=reserva["total_pagar"],
            fecha_reserva=reserva["fecha_reserva"],
            fecha_expiracion_pago=reserva.get("fecha_expiracion_pago"),
            extras=extras_out,
            es_multiproducto=True,
            items=items_out,
            es_paquete=bool(reserva.get("es_paquete")),
            descuento_paquete_pct=reserva.get("descuento_paquete_pct"),
        )

    vuelo = await vuelos_repo.obtener_vuelo(reserva["vuelo_id"])
    tarifa = await vuelos_repo.obtener_tarifa(reserva["tarifa_id"])
    aerolinea = await vuelos_repo.obtener_aerolinea(vuelo["aerolinea_id"])
    nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])

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
        extras=extras_out,
        es_paquete=bool(reserva.get("es_paquete")),
        descuento_paquete_pct=reserva.get("descuento_paquete_pct"),
    )


async def _contexto_checkout(usuario: dict, tarifa_id: str, **extra) -> dict | None:
    vuelos_repo = VuelosRepository()
    tarifa = await vuelos_repo.obtener_tarifa(tarifa_id)
    if tarifa is None:
        return None
    vuelo = await vuelos_repo.obtener_vuelo(tarifa["vuelo_id"])
    aerolinea = await vuelos_repo.obtener_aerolinea(vuelo["aerolinea_id"])
    nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
    # RF-VUE-012: en tarifa Light, un asiento estándar (no premium) solo se
    # puede elegir cuando abre la ventana de check-in gratis — el picker del
    # checkout usa esto para deshabilitar los estándar mientras tanto (los
    # premium siempre están habilitados, se pagan de inmediato).
    seleccion_estandar_habilitada = bool(
        nivel.get("seleccion_asiento_temprana")
    ) or await ventana_checkin_abierta(
        vuelos_repo, vuelo, datetime.datetime.now(datetime.timezone.utc)
    )
    contexto = {
        "usuario": usuario,
        "tarifa": tarifa,
        "vuelo": vuelo,
        "aerolinea": aerolinea,
        "nivel": nivel,
        "origen_legible": await resolver_aeropuerto(vuelo["origen_codigo"]),
        "destino_legible": await resolver_aeropuerto(vuelo["destino_codigo"]),
        "extras_disponibles": await _extras_disponibles(ReservasRepository()),
        "seleccion_estandar_habilitada": seleccion_estandar_habilitada,
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
    asiento_id: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
):
    extras_disponibles = await _extras_disponibles(ReservasRepository())
    extras_data = [e for e in extras_disponibles if e["tipo"] in extras]

    try:
        reserva = await crear_reserva(
            usuario, tarifa_id, precio_esperado, extras_data, asiento_id=asiento_id or None
        )
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
    except (AsientoNoValido, AsientoNoDisponible):
        contexto = await _contexto_checkout(
            usuario, tarifa_id, error="Ese asiento ya no está disponible. Elige otro."
        )
        return templates.TemplateResponse(request, "checkout.html", contexto, status_code=409)
    except SeleccionNoPermitidaAun:
        contexto = await _contexto_checkout(
            usuario,
            tarifa_id,
            error="Ese asiento estándar todavía no se puede elegir en esta tarifa — se habilita cerca del check-in, o puedes elegir uno premium ahora.",
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
async def detalle(
    request: Request,
    reserva_id: str,
    volver_a: str | None = None,
    usuario: dict = Depends(verificar_sesion),
):
    """`volver_a` (WP-04, auditoría de WorkPanels, 2026-07-31) — presente
    solo cuando se llega desde el panel de backoffice (nunca desde
    "Mis reservas" del portal, que no lo manda): decide el shell (topbar de
    backoffice en vez del portal) y el link de "volver" (J10 de la
    constitución — toda pantalla de navegación normal necesita uno que
    funcione, esta no lo tenía para el personal)."""
    es_backoffice = bool(volver_a)
    ruta_volver = urlsplit(volver_a).path if volver_a else ""
    contexto_extra = {
        "layout_base": "layout_app.html" if es_backoffice else "layout_portal.html",
        "volver_a": volver_a if es_backoffice else "/mis-reservas",
        "volver_texto": ETIQUETAS_VOLVER.get(ruta_volver, "Volver") if es_backoffice else "Mis reservas",
    }
    base_contexto = await nav_context(usuario) if es_backoffice else {"usuario": usuario}

    repo = ReservasRepository()
    reserva = await repo.obtener_reserva(reserva_id)
    if reserva is None:
        return templates.TemplateResponse(
            request, "detalle_reserva.html", {**base_contexto, **contexto_extra, "reserva": None}, status_code=404
        )

    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    es_titular = pasajero is not None and reserva["pasajero_titular_id"] == pasajero["id"]
    es_agente_de_la_reserva = reserva.get("agente_id") == usuario["id"]
    autorizado = (
        es_titular
        or es_agente_de_la_reserva
        or await tiene_permiso(usuario, "reservas", "eliminar")
    )
    if not autorizado:
        return templates.TemplateResponse(
            request, "detalle_reserva.html", {**base_contexto, **contexto_extra, "reserva": None}, status_code=404
        )

    detalle_reserva = await construir_detalle(reserva)
    return templates.TemplateResponse(
        request, "detalle_reserva.html", {**base_contexto, **contexto_extra, "reserva": detalle_reserva}
    )


@router.post("/{reserva_id}/cancelar")
async def cancelar(
    reserva_id: str,
    volver_a: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
):
    """`volver_a` (opcional, WP-01/04 — auditoría de WorkPanels) — permite
    que el panel de backoffice (`/backoffice/reservas/reporte`) redirija de
    vuelta a la lista en vez de a esta misma reserva (comportamiento del
    portal, sin cambios cuando no se manda el campo)."""
    destino_base = volver_a or f"/reservas/{reserva_id}"
    try:
        await cancelar_reserva(usuario, reserva_id)
    except ReservaNoEncontradaCancelar:
        return redirect_con_mensaje(volver_a or "/reservas", "Reserva no encontrada", tipo="error")
    except SinPermisoCancelar:
        return redirect_con_mensaje(volver_a or "/reservas", "Sin permiso sobre esa reserva", tipo="error")
    except VueloYaCompletado:
        return redirect_con_mensaje(
            destino_base, "No es posible cancelar un vuelo ya realizado", tipo="error"
        )
    return redirect_con_mensaje(destino_base, "Reserva cancelada")


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
