"""RF-DIS-005 (CU-O31) — historial de notificaciones: propio (pasajero) y
de backoffice (Agente/Admin, dentro de su alcance RBAC Nivel 2)."""

import datetime

from fastapi import APIRouter, Depends, Query, Request

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.rbac_service import requiere_permiso
from app.seguridad.services.session_service import verificar_sesion
from app.shared.csv_export import csv_response
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates
from app.vuelos.repositories.vuelos_repo import VuelosRepository

router = APIRouter()

ESTADOS_ENVIO = ["pendiente", "enviado", "fallido", "fallido_definitivo"]


async def _con_codigo_reserva(notificaciones: list[dict]) -> list[dict]:
    reservas_repo = ReservasRepository()
    salida = []
    for n in notificaciones:
        reserva = await reservas_repo.obtener_reserva(n["reserva_id"])
        salida.append({**n, "codigo_reserva": reserva["codigo_reserva"] if reserva else "", "_reserva": reserva})
    return salida


async def _solo_reservas_pasadas(notificaciones: list[dict]) -> list[dict]:
    """CU-T49 — el pasajero solo ve disrupciones de reservas cuyo vuelo ya
    salió; una disrupción de un vuelo futuro pertenece al flujo normal de
    notificaciones activas, no a "historial"."""
    vuelos_repo = VuelosRepository()
    ahora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    salida = []
    for n in notificaciones:
        reserva = n.pop("_reserva", None)
        vuelo_id = reserva.get("vuelo_id") if reserva else None
        if not vuelo_id:
            continue
        vuelo = await vuelos_repo.obtener_vuelo(vuelo_id)
        if vuelo and vuelo.get("fecha_salida", "") < ahora:
            salida.append(n)
    return salida


@router.get("/notificaciones")
async def mis_notificaciones(
    request: Request,
    canal: str | None = None,
    estado_envio: str | None = None,
    usuario: dict = Depends(verificar_sesion),
):
    repo = DisrupcionesRepository()
    pasajeros_repo = PasajerosRepository()
    pasajero = await pasajeros_repo.pasajero_de_usuario(usuario["id"])

    notificaciones = []
    if pasajero is not None:
        notificaciones = await repo.notificaciones_de_pasajero(pasajero["id"], canal=canal, estado_envio=estado_envio)
    notificaciones = await _con_codigo_reserva(notificaciones)
    notificaciones = await _solo_reservas_pasadas(notificaciones)

    return templates.TemplateResponse(
        request,
        "historial_notificaciones.html",
        {
            "usuario": usuario,
            "notificaciones": notificaciones,
            "filtro_canal": canal or "",
            "filtro_estado": estado_envio or "",
            "es_backoffice": False,
            "layout_base": "layout_portal.html",
        },
    )


async def _notificaciones_filtradas(
    canal: str | None, estado_envio: str | None, desde: str | None, hasta: str | None
) -> list[dict]:
    repo = DisrupcionesRepository()
    filtro_campos = {}
    if canal:
        filtro_campos["canal"] = canal
    if estado_envio:
        filtro_campos["estado_envio"] = estado_envio
    notificaciones = await repo.listar_notificaciones(filtro_campos or None, desde=desde or None, hasta=hasta or None)
    return await _con_codigo_reserva(notificaciones)


@router.get("/backoffice/notificaciones")
async def notificaciones_backoffice(
    request: Request,
    canal: str | None = None,
    estado_envio: str | None = None,
    desde: str = Query(""),
    hasta: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("disrupciones", "ver", "notificaciones")),
):
    # IS-12 (auditoría de informes simples, sesión 2026-08-01) — filtro de
    # período + paginación 25/página, agregados sobre el listado ya
    # existente. La colección real es `notificaciones` (vinculada a
    # `disrupciones` por `disrupcion_id`), no `disrupciones` directamente.
    notificaciones = await _notificaciones_filtradas(canal, estado_envio, desde, hasta)
    pagina = paginar(notificaciones, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "estados_envio": ESTADOS_ENVIO,
            "filtro_canal": canal or "",
            "filtro_estado": estado_envio or "",
            "filtro_desde": desde,
            "filtro_hasta": hasta,
            "es_backoffice": True,
            "layout_base": "layout_app.html",
        }
    )
    return templates.TemplateResponse(request, "historial_notificaciones.html", contexto)


@router.get("/backoffice/notificaciones/exportar")
async def exportar_notificaciones(
    canal: str | None = None,
    estado_envio: str | None = None,
    desde: str = Query(""),
    hasta: str = Query(""),
    usuario: dict = Depends(requiere_permiso("disrupciones", "ver", "notificaciones")),
):
    notificaciones = await _notificaciones_filtradas(canal, estado_envio, desde, hasta)
    return csv_response(
        notificaciones,
        [
            ("fecha", lambda n: n.get("created", "")),
            ("codigo_reserva", lambda n: n.get("codigo_reserva", "")),
            ("canal", lambda n: n.get("canal", "")),
            ("asunto", lambda n: n.get("asunto", "")),
            ("estado_envio", lambda n: n.get("estado_envio", "")),
        ],
        "notificaciones_disrupcion.csv",
    )
