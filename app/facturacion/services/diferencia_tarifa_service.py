"""RF-FAC-007 (CU-O47) — cobrar o reembolsar la diferencia exacta de un
cambio de tarifa. Reutiliza el mecanismo de cobro de la Fase 1 y el de
reembolso de la Fase 4 — el monto es siempre la diferencia, nunca el total
de la reserva.
"""

import datetime
import uuid

from app.facturacion.integrations.payment_gateway import PAYMENT_METHOD_EXITOSO, cobrar, reembolsar
from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.vuelos.repositories.vuelos_repo import VuelosRepository


class PagoOriginalNoEncontrado(Exception):
    pass


class CobroDiferenciaRechazado(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def _politica_vigente_id(reserva: dict) -> str:
    """`reembolsos.politica_aplicada_id` es una relación requerida — para un
    reembolso de diferencia (no una cancelación) se referencia la política
    de la tarifa vigente de la reserva; el motivo real queda en `motivo`."""
    vuelos_repo = VuelosRepository()
    tarifa = await vuelos_repo.obtener_tarifa(reserva["tarifa_id"])
    nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
    return nivel["politica_reembolso_id"]


async def cobrar_o_reembolsar_diferencia(reserva_id: str, monto_diferencia: float) -> dict:
    reservas_repo = ReservasRepository()
    facturacion_repo = FacturacionRepository()

    reserva = await reservas_repo.obtener_reserva(reserva_id)
    pago_original = await facturacion_repo.pago_exitoso_de_reserva(reserva_id)
    if pago_original is None:
        raise PagoOriginalNoEncontrado()

    monto = round(abs(monto_diferencia), 2)
    ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")

    if monto_diferencia > 0:
        metodo = await facturacion_repo.metodo_pago_por_defecto()
        resultado = await cobrar(
            monto,
            PAYMENT_METHOD_EXITOSO,
            idempotency_key=f"reserva-{reserva_id}-diferencia-{uuid.uuid4().hex[:10]}",
            descripcion=f"Diferencia de tarifa — reserva {reserva['codigo_reserva']}",
        )
        if resultado["status"] != "succeeded":
            raise CobroDiferenciaRechazado(resultado.get("motivo", "Pago rechazado"))

        pago = await facturacion_repo.crear_pago(
            {
                "reserva_id": reserva_id,
                "monto": monto,
                "moneda": "USD",
                "metodo_pago_id": metodo["id"],
                "stripe_payment_intent_id": resultado["id"],
                "estado": "exitoso",
                "fecha_pago": ahora_iso,
            }
        )
        await AuditService().insertar(
            "cobro_diferencia_tarifa",
            "pagos",
            registro_id=pago["id"],
            detalle={"monto": monto, "reserva_id": reserva_id},
        )
        return {"tipo": "cobro", **pago}

    if monto_diferencia < 0:
        resultado = await reembolsar(pago_original["stripe_payment_intent_id"], monto)
        politica_id = await _politica_vigente_id(reserva)
        reembolso = await facturacion_repo.crear_reembolso(
            {
                "pago_id": pago_original["id"],
                "reserva_id": reserva_id,
                "politica_aplicada_id": politica_id,
                "motivo": "Diferencia de tarifa a favor del pasajero",
                "monto": monto,
                "estado": "procesado" if resultado["status"] == "succeeded" else "rechazado",
                "stripe_refund_id": resultado["id"],
                "fecha_solicitud": ahora_iso,
                "fecha_procesado": ahora_iso,
            }
        )
        await AuditService().insertar(
            "reembolso_diferencia_tarifa",
            "reembolsos",
            registro_id=reembolso["id"],
            detalle={"monto": monto, "reserva_id": reserva_id},
        )
        return {"tipo": "reembolso", **reembolso}

    return {"tipo": "sin_cambio"}
