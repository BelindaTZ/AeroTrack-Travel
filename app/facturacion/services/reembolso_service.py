"""RF-FAC-006 (CU-O37), RN-FAC-001 — reembolso de una reserva pagada.

El monto se calcula aquí a partir de la política de reembolso real de la
tarifa comprada — la firma de `procesar_reembolso` no acepta un monto
manual, así que no existe ninguna vía de override (RN-FAC-001).
"""

import datetime

from app.facturacion.integrations.payment_gateway import reembolsar
from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.vuelos.repositories.vuelos_repo import VuelosRepository


class PagoNoEncontrado(Exception):
    pass


class ReembolsoNoAplicable(Exception):
    """La política de la tarifa comprada no permite ningún reembolso (0%)."""


async def _resolver_politica(reserva: dict) -> dict:
    vuelos_repo = VuelosRepository()
    tarifa = await vuelos_repo.obtener_tarifa(reserva["tarifa_id"])
    nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
    return await vuelos_repo.politica_reembolso(nivel["politica_reembolso_id"])


async def procesar_reembolso(reserva_id: str, motivo: str) -> dict:
    reservas_repo = ReservasRepository()
    facturacion_repo = FacturacionRepository()

    reserva = await reservas_repo.obtener_reserva(reserva_id)
    pago = await facturacion_repo.pago_exitoso_de_reserva(reserva_id)
    if pago is None:
        raise PagoNoEncontrado()

    politica = await _resolver_politica(reserva)
    if politica["porcentaje_reembolso"] <= 0:
        raise ReembolsoNoAplicable()

    monto = round(pago["monto"] * politica["porcentaje_reembolso"] / 100, 2)

    resultado = await reembolsar(pago["stripe_payment_intent_id"], monto)

    ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    reembolso = await facturacion_repo.crear_reembolso(
        {
            "pago_id": pago["id"],
            "reserva_id": reserva_id,
            "politica_aplicada_id": politica["id"],
            "motivo": motivo,
            "monto": monto,
            "estado": "procesado" if resultado["status"] == "succeeded" else "rechazado",
            "stripe_refund_id": resultado["id"],
            "fecha_solicitud": ahora_iso,
            "fecha_procesado": ahora_iso,
        }
    )

    if resultado["status"] == "succeeded":
        await facturacion_repo.actualizar_pago(pago["id"], {"estado": "reembolsado"})

    await AuditService().insertar(
        "reembolso_procesado",
        "reembolsos",
        usuario_id=None,
        registro_id=reembolso["id"],
        detalle={"monto": monto, "porcentaje_aplicado": politica["porcentaje_reembolso"]},
    )

    return reembolso
