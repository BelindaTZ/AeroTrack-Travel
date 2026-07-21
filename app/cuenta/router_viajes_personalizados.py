"""RF-CTA-004 — Crear viaje personalizado (planificación libre, sin reserva)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates

router = APIRouter()


async def _pasajero_id(usuario: dict) -> str | None:
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    return pasajero["id"] if pasajero else None


@router.get("/viajes-personalizados")
async def listar(request: Request, usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    viajes = await CuentaRepository().listar_viajes_personalizados(pasajero_id) if pasajero_id else []
    return templates.TemplateResponse(request, "viajes_personalizados.html", {"usuario": usuario, "viajes": viajes})


@router.post("/viajes-personalizados")
async def crear(nombre: str = Form(...), descripcion: str = Form(""), usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    if pasajero_id is None:
        return RedirectResponse(
            "/vuelos/buscar?mensaje=Solo cuentas de pasajero pueden planificar viajes", status_code=303
        )
    viaje = await CuentaRepository().crear_viaje_personalizado(pasajero_id, nombre, descripcion)
    await AuditService().insertar(
        "crear_viaje_personalizado", "viajes_personalizados", usuario_id=usuario["id"], registro_id=viaje["id"]
    )
    return RedirectResponse("/viajes-personalizados?mensaje=Viaje creado", status_code=303)


@router.post("/viajes-personalizados/{viaje_id}/eliminar")
async def eliminar(viaje_id: str, usuario: dict = Depends(verificar_sesion)):
    repo = CuentaRepository()
    viaje = await repo.obtener_viaje_personalizado(viaje_id)
    pasajero_id = await _pasajero_id(usuario)
    if viaje is None or pasajero_id is None or viaje["pasajero_id"] != pasajero_id:
        return RedirectResponse("/viajes-personalizados?mensaje=No se pudo eliminar", status_code=303)

    await repo.eliminar_viaje_personalizado(viaje_id)
    await AuditService().insertar(
        "eliminar_viaje_personalizado", "viajes_personalizados", usuario_id=usuario["id"], registro_id=viaje_id
    )
    return RedirectResponse("/viajes-personalizados?mensaje=Viaje eliminado", status_code=303)
