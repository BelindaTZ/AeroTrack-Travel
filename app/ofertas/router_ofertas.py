"""RF-OFE-001,002,004,005 (CU-O101,O102,O104,O105) — ofertas destacadas,
destinos populares (estadística real, no editorial), newsletter y
términos — todo público, sesión opcional. Sin prefijo común: los paths
reales del spec (`/ofertas`, `/destinos-populares`, `/newsletter/
suscribirse`) no comparten un mismo namespace."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.ofertas.repositories.ofertas_repo import OfertasRepository
from app.ofertas.services.ofertas_service import destinos_populares as _destinos_populares
from app.ofertas.services.ofertas_service import ofertas_destacadas_con_descripcion, suscribirse_newsletter
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import usuario_opcional
from app.shared.templating import templates

router = APIRouter()


async def _pasajero_id(usuario: dict | None) -> str | None:
    if not usuario or usuario.get("tipo_actor") != "pasajero":
        return None
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    return pasajero["id"] if pasajero else None


@router.get("/ofertas")
async def listar(request: Request, tipo_producto: str | None = None, usuario: dict | None = Depends(usuario_opcional)):
    ofertas = await ofertas_destacadas_con_descripcion(tipo_producto)
    return templates.TemplateResponse(
        request, "ofertas.html", {"usuario": usuario, "ofertas": ofertas, "tipo_producto": tipo_producto or ""}
    )


@router.get("/ofertas/{oferta_id}/terminos")
async def terminos(request: Request, oferta_id: str, usuario: dict | None = Depends(usuario_opcional)):
    oferta = await OfertasRepository().obtener_oferta(oferta_id)
    return templates.TemplateResponse(
        request, "terminos_oferta.html", {"usuario": usuario, "oferta": oferta}, status_code=200 if oferta else 404
    )


@router.get("/destinos-populares")
async def destinos_populares_view(
    request: Request, origen: str | None = None, usuario: dict | None = Depends(usuario_opcional)
):
    pasajero_id = await _pasajero_id(usuario)
    origen_usado, destinos = await _destinos_populares(pasajero_id, origen.upper() if origen else None)
    return templates.TemplateResponse(
        request, "destinos_populares.html", {"usuario": usuario, "destinos": destinos, "origen": origen_usado or ""}
    )


@router.post("/newsletter/suscribirse")
async def newsletter(
    email: str = Form(...), next: str | None = Form(None), usuario: dict | None = Depends(usuario_opcional)
):
    pasajero_id = await _pasajero_id(usuario)
    await suscribirse_newsletter(email, pasajero_id)
    return RedirectResponse(f"{next or '/ofertas'}?mensaje=Te suscribiste al newsletter", status_code=303)
