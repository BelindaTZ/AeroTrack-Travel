"""RF-FAC-002/007 — generación de PDFs (factura, itinerario) con ReportLab.

Único punto del sistema que usa el SDK de ReportLab; el resto de Facturación
solo pide bytes a este módulo y los sube a PocketBase vía el repositorio.
"""

import asyncio
import io

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def _dibujar_encabezado(c: canvas.Canvas, titulo: str) -> None:
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 760, "AeroTrack Travel")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(72, 735, titulo)
    c.line(72, 725, 540, 725)


def _generar_pdf_factura_sync(numero_factura: str, reserva: dict, pago: dict) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    _dibujar_encabezado(c, "Factura")

    c.setFont("Helvetica", 11)
    y = 690
    filas = [
        ("Factura N°", numero_factura),
        ("Reserva", reserva.get("codigo_reserva", "")),
        ("Fecha de pago", (pago.get("fecha_pago") or "")[:10]),
        ("Método", "Tarjeta (Stripe test mode)"),
        ("Estado del pago", pago.get("estado", "")),
    ]
    for etiqueta, valor in filas:
        c.drawString(72, y, f"{etiqueta}:")
        c.drawString(220, y, str(valor))
        y -= 20

    y -= 10
    c.line(72, y, 540, y)
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, y, "Total")
    c.drawRightString(540, y, f"${pago['monto']:.2f} {pago.get('moneda', 'USD')}")

    c.showPage()
    c.save()
    return buffer.getvalue()


async def generar_pdf_factura(numero_factura: str, reserva: dict, pago: dict) -> bytes:
    return await asyncio.to_thread(_generar_pdf_factura_sync, numero_factura, reserva, pago)


def _generar_pdf_itinerario_sync(reserva: dict, vuelo: dict, aerolinea: dict) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    _dibujar_encabezado(c, "Itinerario de vuelo")

    c.setFont("Helvetica", 11)
    y = 690
    filas = [
        ("Reserva", reserva.get("codigo_reserva", "")),
        ("Aerolínea", aerolinea.get("nombre", "")),
        ("Vuelo", vuelo.get("numero_vuelo", "")),
        ("Ruta", f"{vuelo.get('origen_codigo', '')} → {vuelo.get('destino_codigo', '')}"),
        ("Fecha de salida", (vuelo.get("fecha_salida") or "")[:10]),
        ("Hora de salida", vuelo.get("hora_salida_programada", "")),
        ("Hora de llegada", vuelo.get("hora_llegada_programada", "")),
        ("Estado de la reserva", reserva.get("estado", "")),
    ]
    for etiqueta, valor in filas:
        c.drawString(72, y, f"{etiqueta}:")
        c.drawString(220, y, str(valor))
        y -= 20

    c.showPage()
    c.save()
    return buffer.getvalue()


async def generar_pdf_itinerario(reserva: dict, vuelo: dict, aerolinea: dict) -> bytes:
    return await asyncio.to_thread(_generar_pdf_itinerario_sync, reserva, vuelo, aerolinea)
