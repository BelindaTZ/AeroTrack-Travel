"""Punto de integración real para el futuro webhook de pago de Facturación
(CU-O32). Facturación no existe en esta sesión — `confirmar_pago_reserva`
es la única forma de representar "el pago se confirmó" hasta entonces.
Cuando Facturación exista, su webhook de Stripe llama esta misma función;
no hay que reescribir la lógica de estado de la reserva.

Permite implementar y probar de verdad RN-RES-005 (QP-04, la condición de
carrera entre el pago y la expiración automática) sin necesitar Stripe.
"""

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.services.reserva_locks import locks
from app.seguridad.services.audit_service import AuditService
from app.vuelos.services.cupo_service import verificar_y_reservar_cupo


class ReservaNoEncontrada(Exception):
    pass


async def confirmar_pago_reserva(reserva_id: str) -> dict:
    repo = ReservasRepository()

    # El lock por reserva_id es lo que hace real la garantía de RN-RES-005:
    # sin él, esta función podría leer "pendiente_pago" justo antes de que
    # `expiracion_service` la cancele y libere el cupo, y luego escribir
    # "confirmada" a ciegas sobre ese estado ya obsoleto — una reserva
    # confirmada sin cupo real detrás. El lock serializa ambas rutas.
    async with locks[reserva_id]:
        reserva = await repo.obtener_reserva(reserva_id)
        if reserva is None:
            raise ReservaNoEncontrada()

        if reserva["estado"] == "pendiente_pago":
            return await repo.actualizar_reserva(reserva_id, {"estado": "confirmada"})

        if reserva["estado"] == "cancelada":
            # RN-RES-005 (QP-04): el pago llegó después de que la expiración
            # automática ya canceló la reserva. Nunca se descarta un pago
            # exitoso — se intenta re-confirmar tomando cupo de nuevo; si ya
            # no queda, se marca para reembolso inmediato (Facturación no
            # existe todavía: se documenta en auditoría en vez de dispararse
            # un cobro real, mismo patrón que Vuelos con Disrupciones).
            if await verificar_y_reservar_cupo(reserva["tarifa_id"]):
                actualizada = await repo.actualizar_reserva(reserva_id, {"estado": "confirmada"})
                await AuditService().insertar(
                    "reconfirmar_tras_expiracion",
                    "reservas",
                    registro_id=reserva_id,
                    detalle={"motivo": "pago_llego_despues_de_expiracion", "cupo_recuperado": True},
                )
                return actualizada

            await AuditService().insertar(
                "pago_sin_cupo_tras_expiracion",
                "reservas",
                registro_id=reserva_id,
                detalle={"estado": "reembolso_inmediato_pendiente_de_modulo_facturacion"},
            )
            return reserva

        return reserva  # confirmada/modificada/completada: idempotente (REG-D1)
