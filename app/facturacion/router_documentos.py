"""RF-FAC-009,010 — descarga de factura (persistida) e itinerario (on-demand)."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.services.documentos_service import generar_pdf_itinerario
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.services.voucher_service import obtener_o_generar_voucher
from app.seguridad.services.rbac_service import tiene_permiso
from app.seguridad.services.session_service import verificar_sesion
from app.vuelos.repositories.vuelos_repo import VuelosRepository

router = APIRouter()


async def _autorizado(usuario: dict, reserva: dict, pasajero: dict | None, modulo: str) -> bool:
    es_titular = pasajero is not None and reserva["pasajero_titular_id"] == pasajero["id"]
    es_agente = reserva.get("agente_id") == usuario["id"]
    if es_titular or es_agente:
        return True
    return await tiene_permiso(usuario, modulo, "eliminar")


@router.get("/facturas/{factura_id}/pdf")
async def descargar_factura(factura_id: str, usuario: dict = Depends(verificar_sesion)):
    facturacion_repo = FacturacionRepository()
    reservas_repo = ReservasRepository()

    factura = await facturacion_repo.obtener_factura(factura_id)
    if factura is None:
        raise HTTPException(status_code=404)

    reserva = await reservas_repo.obtener_reserva(factura["reserva_id"])
    pasajero = await reservas_repo.pasajero_de_usuario(usuario["id"])
    if reserva is None or not await _autorizado(usuario, reserva, pasajero, "facturacion"):
        raise HTTPException(status_code=404)

    contenido = await facturacion_repo.descargar_pdf_factura(factura["id"], factura["archivo_pdf"])
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{factura["numero_factura"]}.pdf"'},
    )


@router.get("/reservas/{reserva_id}/itinerario-pdf")
async def descargar_itinerario(reserva_id: str, usuario: dict = Depends(verificar_sesion)):
    reservas_repo = ReservasRepository()
    vuelos_repo = VuelosRepository()

    reserva = await reservas_repo.obtener_reserva(reserva_id)
    pasajero = await reservas_repo.pasajero_de_usuario(usuario["id"])
    if reserva is None or not await _autorizado(usuario, reserva, pasajero, "reservas"):
        raise HTTPException(status_code=404)

    vuelo = await vuelos_repo.obtener_vuelo(reserva["vuelo_id"])
    aerolinea = await vuelos_repo.obtener_aerolinea(vuelo["aerolinea_id"]) if vuelo else {}

    # On-demand — no se persiste, siempre refleja el estado actual de la reserva.
    pdf_bytes = await generar_pdf_itinerario(reserva, vuelo or {}, aerolinea)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="itinerario-{reserva["codigo_reserva"]}.pdf"'
        },
    )


@router.get("/reservas/{reserva_id}/voucher-pdf")
async def descargar_voucher(reserva_id: str, usuario: dict = Depends(verificar_sesion)):
    """RF-RES-009 — a diferencia del itinerario, este SÍ es el mismo archivo
    persistido en cada descarga (mismo patrón que /facturas/{id}/pdf)."""
    reservas_repo = ReservasRepository()

    reserva = await reservas_repo.obtener_reserva(reserva_id)
    pasajero = await reservas_repo.pasajero_de_usuario(usuario["id"])
    if reserva is None or not await _autorizado(usuario, reserva, pasajero, "reservas"):
        raise HTTPException(status_code=404)

    contenido, reserva = await obtener_o_generar_voucher(reserva)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="voucher-{reserva["codigo_reserva"]}.pdf"'
        },
    )
