"""RF-FAC-002 (CU-O33) — emitir factura sobre un pago exitoso."""

import datetime
import uuid

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.services.documentos_service import generar_pdf_factura
from app.shared.pocketbase_client import get_pocketbase_client


async def emitir_factura(reserva: dict, pago: dict) -> dict:
    repo = FacturacionRepository()
    ahora = datetime.datetime.now(datetime.timezone.utc)
    numero_factura = f"FAC-{ahora:%Y%m}-{uuid.uuid4().hex[:8].upper()}"

    factura = await repo.crear_factura(
        {
            "reserva_id": reserva["id"],
            "pago_id": pago["id"],
            "numero_factura": numero_factura,
            "total": pago["monto"],
            "fecha_emision": ahora.strftime("%Y-%m-%d %H:%M:%S.000Z"),
        }
    )

    pdf_bytes = await generar_pdf_factura(numero_factura, reserva, pago)
    client = get_pocketbase_client()
    factura = await client.update_record_con_archivo(
        "facturas",
        factura["id"],
        {},
        {"archivo_pdf": (f"{numero_factura}.pdf", pdf_bytes, "application/pdf")},
    )
    return factura
