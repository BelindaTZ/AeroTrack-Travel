"""RF-RES-009 — comprobante de reserva persistido (`reservas.voucher_pdf`),
mismo patrón que `facturas.archivo_pdf` (RF-FAC-002): se genera una sola vez
y desde ahí se sirve el mismo archivo, a diferencia del itinerario (efímero).
"""

from app.facturacion.services.documentos_service import generar_pdf_voucher
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.vuelos.repositories.vuelos_repo import VuelosRepository


async def emitir_voucher(reserva: dict) -> dict:
    repo = ReservasRepository()
    vuelos_repo = VuelosRepository()

    pasajeros = await repo.pasajeros_de_reserva(reserva["id"])
    nombres = [await repo.nombre_de_pasajero(p["pasajero_id"]) for p in pasajeros]

    vuelo = None
    aerolinea = None
    if reserva.get("vuelo_id"):
        vuelo = await vuelos_repo.obtener_vuelo(reserva["vuelo_id"])
        if vuelo is not None:
            aerolinea = await vuelos_repo.obtener_aerolinea(vuelo["aerolinea_id"])

    pdf_bytes = await generar_pdf_voucher(reserva, nombres, vuelo, aerolinea)
    return await repo.guardar_voucher(
        reserva["id"], f"voucher-{reserva['codigo_reserva']}.pdf", pdf_bytes
    )


async def obtener_o_generar_voucher(reserva: dict) -> tuple[bytes, dict]:
    """Sirve el voucher ya persistido; si todavía no existe (reserva creada
    antes de este RF, o el hook de emisión no corrió por algún motivo), lo
    genera y lo persiste en el momento — autocorrectivo, no bloquea al
    pasajero por un detalle de cuándo se implementó esto."""
    repo = ReservasRepository()
    if not reserva.get("voucher_pdf"):
        reserva = await emitir_voucher(reserva)
    contenido = await repo.descargar_voucher(reserva["id"], reserva["voucher_pdf"])
    return contenido, reserva
