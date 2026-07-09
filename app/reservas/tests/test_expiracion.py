import asyncio
import datetime

from app.reservas.services.expiracion_service import expirar_pendientes
from app.reservas.services.pago_stub_service import confirmar_pago_reserva


def _pasado_iso(minutos: int = 5) -> str:
    momento = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutos)
    return momento.strftime("%Y-%m-%d %H:%M:%S.000Z")


def _futuro_iso(minutos: int = 15) -> str:
    momento = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutos)
    return momento.strftime("%Y-%m-%d %H:%M:%S.000Z")


# ── RF-RES-007 / RN-RES-004 (CHK009, CHK013) ──────────────────────────────

async def test_expirar_pendientes_cancela_y_libera_cupo_exacto(
    pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=4)  # ya "tomó" 1 cupo
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"],
        estado="pendiente_pago", fecha_expiracion_pago=_pasado_iso(),
    )

    cantidad = await expirar_pendientes()
    assert cantidad >= 1

    actualizada = await pb.get_record("reservas", reserva["id"])
    assert actualizada["estado"] == "cancelada"

    tarifa_actualizada = await pb.get_record("tarifas_vuelo", tarifa["id"])
    assert tarifa_actualizada["cupos_disponibles"] == 5  # exactamente +1, ni más ni menos


async def test_expirar_pendientes_no_toca_reserva_vigente(
    pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"],
        estado="pendiente_pago", fecha_expiracion_pago=_futuro_iso(),
    )

    await expirar_pendientes()

    sin_cambios = await pb.get_record("reservas", reserva["id"])
    assert sin_cambios["estado"] == "pendiente_pago"


# ── RN-RES-005 / QP-04 (CHK014) ───────────────────────────────────────────

async def test_pago_confirmado_tras_expiracion_nunca_deja_huerfana(
    pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=5)
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"],
        estado="pendiente_pago", fecha_expiracion_pago=_pasado_iso(),
    )

    resultados = await asyncio.gather(
        expirar_pendientes(), confirmar_pago_reserva(reserva["id"]), return_exceptions=True
    )
    assert not any(isinstance(r, Exception) for r in resultados), resultados

    final = await pb.get_record("reservas", reserva["id"])
    # El pago nunca se pierde: la reserva queda confirmada, sin importar el
    # orden de ejecución real (directo, o re-confirmada tras la expiración
    # porque había cupo disponible).
    assert final["estado"] == "confirmada"
