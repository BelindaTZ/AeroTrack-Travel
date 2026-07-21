"""RF-CTA-003 — Ver y retomar búsquedas recientes. La escritura es
responsabilidad de cada módulo de producto (RN-CTA-001,
`app.shared.busqueda_reciente`) — este router solo lee y relanza."""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.cuenta.schemas import BusquedaRecienteOut
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates

router = APIRouter()

_RUTA_POR_TIPO = {
    "vuelo": "/vuelos/buscar",
    "hotel": "/hoteles/buscar",
    "auto": "/autos/buscar",
    "actividad": "/actividades/buscar",
    "crucero": "/cruceros/buscar",
}


async def _pasajero_id(usuario: dict) -> str | None:
    pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
    return pasajero["id"] if pasajero else None


def _href(busqueda: dict) -> str:
    base = _RUTA_POR_TIPO.get(busqueda["tipo_producto"])
    if base is None:
        return "/"
    return f"{base}?{urlencode(busqueda['criterios'])}"


@router.get("/mis-busquedas-recientes")
async def listar(request: Request, usuario: dict = Depends(verificar_sesion)):
    pasajero_id = await _pasajero_id(usuario)
    crudas = await CuentaRepository().listar_busquedas_recientes(pasajero_id) if pasajero_id else []
    busquedas = [
        BusquedaRecienteOut(
            id=b["id"], tipo_producto=b["tipo_producto"], criterios=b["criterios"], fecha=b["fecha"],
            href_relanzar=_href(b),
        )
        for b in crudas
    ]
    return templates.TemplateResponse(
        request, "busquedas_recientes.html", {"usuario": usuario, "busquedas": busquedas}
    )


@router.post("/mis-busquedas-recientes/{busqueda_id}/relanzar")
async def relanzar(busqueda_id: str, usuario: dict = Depends(verificar_sesion)):
    repo = CuentaRepository()
    busqueda = await repo.obtener_busqueda_reciente(busqueda_id)
    pasajero_id = await _pasajero_id(usuario)
    if busqueda is None or pasajero_id is None or busqueda["pasajero_id"] != pasajero_id:
        return RedirectResponse("/mis-busquedas-recientes?mensaje=Búsqueda no encontrada", status_code=303)
    return RedirectResponse(_href(busqueda), status_code=303)
