"""RF-CTA-002 — Guardar / eliminar favorito (destino, hotel o actividad)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates

router = APIRouter()

TIPOS_VALIDOS = {"destino", "hotel", "actividad"}


async def _pasajero_id(usuario: dict) -> str | None:
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    return pasajero["id"] if pasajero else None


@router.get("/favoritos")
async def listar(request: Request, usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    favoritos = await CuentaRepository().listar_favoritos(pasajero_id) if pasajero_id else []
    return templates.TemplateResponse(request, "favoritos.html", {"usuario": usuario, "favoritos": favoritos})


@router.post("/favoritos")
async def guardar(
    tipo: str = Form(...),
    producto_ref: str = Form(...),
    next: str | None = Form(None),
    usuario: dict = Depends(verificar_sesion),
):
    destino = next or "/favoritos"
    pasajero_id = await _pasajero_id(usuario)
    if pasajero_id is None or tipo not in TIPOS_VALIDOS:
        return RedirectResponse(f"{destino}?mensaje=No se pudo guardar el favorito", status_code=303)

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    favorito = await CuentaRepository().crear_favorito(pasajero_id, tipo, producto_ref, ahora)
    await AuditService().insertar(
        "guardar_favorito", "favoritos", usuario_id=usuario["id"], registro_id=favorito["id"]
    )
    return RedirectResponse(f"{destino}?mensaje=Guardado en favoritos", status_code=303)


@router.post("/favoritos/{favorito_id}/eliminar")
async def eliminar(
    favorito_id: str, next: str | None = Form(None), usuario: dict = Depends(verificar_sesion)
):
    destino = next or "/favoritos"
    repo = CuentaRepository()
    favorito = await repo.obtener_favorito(favorito_id)
    pasajero_id = await _pasajero_id(usuario)
    if favorito is None or pasajero_id is None or favorito["pasajero_id"] != pasajero_id:
        return RedirectResponse(f"{destino}?mensaje=No se pudo eliminar", status_code=303)

    await repo.eliminar_favorito(favorito_id)
    await AuditService().insertar(
        "eliminar_favorito", "favoritos", usuario_id=usuario["id"], registro_id=favorito_id
    )
    return RedirectResponse(f"{destino}?mensaje=Favorito eliminado", status_code=303)
