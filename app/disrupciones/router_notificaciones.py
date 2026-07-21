"""RF-DIS-005 (CU-O31) — historial de notificaciones: propio (pasajero) y
de backoffice (Agente/Admin, dentro de su alcance RBAC Nivel 2)."""

from fastapi import APIRouter, Depends, Request

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.rbac_service import requiere_permiso
from app.seguridad.services.session_service import verificar_sesion
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter()


async def _con_codigo_reserva(notificaciones: list[dict]) -> list[dict]:
    reservas_repo = ReservasRepository()
    salida = []
    for n in notificaciones:
        reserva = await reservas_repo.obtener_reserva(n["reserva_id"])
        salida.append({**n, "codigo_reserva": reserva["codigo_reserva"] if reserva else ""})
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


@router.get("/backoffice/notificaciones")
async def notificaciones_backoffice(
    request: Request,
    canal: str | None = None,
    estado_envio: str | None = None,
    usuario: dict = Depends(requiere_permiso("disrupciones", "ver", "notificaciones")),
):
    repo = DisrupcionesRepository()
    condiciones = []
    if canal:
        condiciones.append(f'canal="{canal}"')
    if estado_envio:
        condiciones.append(f'estado_envio="{estado_envio}"')
    filtro = " && ".join(condiciones) if condiciones else None
    notificaciones = await repo.listar_notificaciones(filtro)
    notificaciones = await _con_codigo_reserva(notificaciones)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "notificaciones": notificaciones,
            "filtro_canal": canal or "",
            "filtro_estado": estado_envio or "",
            "es_backoffice": True,
            "layout_base": "layout_app.html",
        }
    )
    return templates.TemplateResponse(request, "historial_notificaciones.html", contexto)
