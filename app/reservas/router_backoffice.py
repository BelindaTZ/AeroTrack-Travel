"""RF-RES-002 (CU-O22) — crear reserva asistida. Incluye RBAC (CU-O43)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.reservas.services.crear_reserva_service import (
    CupoNoDisponible,
    PasajeroNoEncontrado,
    PrecioDesactualizado,
    TarifaNoEncontrada,
    crear_reserva_asistida,
)
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates
from app.vuelos.repositories.dims_reader import resolver_aeropuerto
from app.vuelos.repositories.vuelos_repo import VuelosRepository

router = APIRouter(prefix="/backoffice/reservas")


async def _contexto_form(usuario: dict, tarifa_id: str | None = None, **extra) -> dict:
    contexto = await nav_context(usuario)
    if tarifa_id:
        vuelos_repo = VuelosRepository()
        tarifa = await vuelos_repo.obtener_tarifa(tarifa_id)
        if tarifa:
            vuelo = await vuelos_repo.obtener_vuelo(tarifa["vuelo_id"])
            aerolinea = await vuelos_repo.obtener_aerolinea(vuelo["aerolinea_id"])
            nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
            contexto.update(
                {
                    "tarifa": tarifa,
                    "vuelo": vuelo,
                    "aerolinea": aerolinea,
                    "nivel": nivel,
                    "origen_legible": await resolver_aeropuerto(vuelo["origen_codigo"]),
                    "destino_legible": await resolver_aeropuerto(vuelo["destino_codigo"]),
                }
            )
    contexto.update(extra)
    return contexto


@router.get("/nueva")
async def nueva_form(
    request: Request,
    tarifa_id: str | None = None,
    usuario: dict = Depends(requiere_permiso("reservas", "crear")),
):
    return templates.TemplateResponse(
        request, "backoffice/reserva_asistida.html", await _contexto_form(usuario, tarifa_id)
    )


@router.post("")
async def crear(
    request: Request,
    email_pasajero: str = Form(...),
    tarifa_id: str = Form(...),
    precio_esperado: float = Form(...),
    usuario: dict = Depends(requiere_permiso("reservas", "crear")),
):
    try:
        reserva = await crear_reserva_asistida(usuario, email_pasajero, tarifa_id, precio_esperado)
    except PasajeroNoEncontrado:
        contexto = await _contexto_form(
            usuario, tarifa_id, error=f"No existe una cuenta de pasajero con el correo {email_pasajero}"
        )
        return templates.TemplateResponse(
            request, "backoffice/reserva_asistida.html", contexto, status_code=404
        )
    except TarifaNoEncontrada:
        contexto = await _contexto_form(usuario, tarifa_id, error="Tarifa no encontrada")
        return templates.TemplateResponse(
            request, "backoffice/reserva_asistida.html", contexto, status_code=404
        )
    except PrecioDesactualizado as exc:
        contexto = await _contexto_form(
            usuario, tarifa_id, error=f"El precio cambió a ${exc.precio_actual:.2f}. Vuelve a intentar."
        )
        return templates.TemplateResponse(
            request, "backoffice/reserva_asistida.html", contexto, status_code=409
        )
    except CupoNoDisponible:
        contexto = await _contexto_form(usuario, tarifa_id, error="Ese vuelo ya no tiene cupo en este nivel de tarifa.")
        return templates.TemplateResponse(
            request, "backoffice/reserva_asistida.html", contexto, status_code=409
        )

    await AuditService().insertar(
        "crear",
        "reservas",
        usuario_id=usuario["id"],
        registro_id=reserva["id"],
        detalle={"canal": "asistida", "codigo_reserva": reserva["codigo_reserva"], "email_pasajero": email_pasajero},
    )
    return RedirectResponse(f"/reservas/{reserva['id']}", status_code=303)
