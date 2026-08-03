import asyncio
import datetime

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc
from app.reservas.services.expiracion_service import expirar_pendientes
from app.reservas.services.pago_stub_service import confirmar_pago_reserva
from app.shared.cupo_service import verificar_y_reservar_cupo


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

    actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert actualizada["estado"] == "cancelada"

    tarifa_actualizada = await moc.obtener("cupos_tarifas_vuelo", tarifa["id"])
    assert tarifa_actualizada["cupos_disponibles"] == 5  # exactamente +1, ni más ni menos


async def test_expirar_pendientes_no_toca_reserva_vigente(
    pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"],
        estado="pendiente_pago", fecha_expiracion_pago=_futuro_iso(),
    )

    await expirar_pendientes()

    sin_cambios = await ReservasRepository().obtener_reserva(reserva["id"])
    assert sin_cambios["estado"] == "pendiente_pago"


# ── RN-RES-005 / QP-04 (CHK014) ───────────────────────────────────────────

# ── RF-HOT-004 (gap real cerrado 2026-07-29) — libera TODAS las noches ────

async def test_expirar_pendientes_hotel_libera_todas_las_noches(pb, pasajero_factory):
    """A diferencia de vuelo (una sola fila de cupo), una reserva de hotel
    abarca N noches — expirar debe liberar TODAS, no solo una (ver
    `app.shared.cupo_rango_service`)."""
    _usuario, pasajero = await pasajero_factory()
    hotel = await pb.create_record(
        "hoteles_catalogo",
        {"nombre": "Hotel Test Expiración", "direccion": "1 Test St", "ciudad": "Paris", "pais": "France",
         "fecha_actualizacion": "2027-01-01 00:00:00.000Z"},
    )
    tarifa = await pb.create_record(
        "hoteles_tarifas",
        {"hotel_id": hotel["id"], "tipo_habitacion": "Standard", "precio_final": 100.0, "moneda": "USD",
         "reembolsable": True, "cupos_disponibles": 5, "fecha_actualizacion": "2027-01-01 00:00:00.000Z"},
    )
    noches = []
    for fecha in ("2027-11-01", "2027-11-02"):
        noches.append(await pb.create_record(
            "hoteles_disponibilidad",
            {"hotel_id": hotel["id"], "hotel_tarifa_id": tarifa["id"], "fecha": fecha,
             "cupos_disponibles": 3, "fecha_actualizacion": "2027-01-01 00:00:00.000Z"},
        ))

    reservas_repo = ReservasRepository()
    reserva = await reservas_repo.crear_reserva(
        {
            "codigo_reserva": "EXPHOTEL1", "pasajero_titular_id": pasajero["id"], "canal": "autoservicio",
            "estado": "pendiente_pago", "es_paquete": False, "total_pagar": 200.0,
            "fecha_reserva": _pasado_iso(60), "fecha_expiracion_pago": _pasado_iso(),
        }
    )
    await reservas_repo.crear_item(
        {
            "reserva_id": reserva["id"], "tipo_producto": "hotel", "hotel_id": hotel["id"],
            "hotel_tarifa_id": tarifa["id"], "precio_final": 200.0, "cantidad": 2,
            "unidades": 1, "fecha_inicio": "2027-11-01", "fecha_fin": "2027-11-03",
            "estado_item": "pendiente",
        }
    )

    # Simula que el checkout ya había reservado 1 unidad en cada noche.
    for noche in noches:
        assert await verificar_y_reservar_cupo("hoteles_disponibilidad", noche["id"], "cupos_disponibles", 1)

    await expirar_pendientes()

    actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert actualizada["estado"] == "cancelada"
    for noche in noches:
        fila = await moc.obtener("cupos_hoteles_disponibilidad", noche["id"])
        assert fila["cupos_disponibles"] == 3  # 2 (reservado) + 1 (liberado) = 3, la original

    for noche in noches:
        await pb.delete_record("hoteles_disponibilidad", noche["id"])
    await pb.delete_record("hoteles_tarifas", tarifa["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])


async def test_pago_confirmado_tras_expiracion_nunca_deja_huerfana(
    pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
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

    final = await ReservasRepository().obtener_reserva(reserva["id"])
    # El pago nunca se pierde: la reserva queda confirmada, sin importar el
    # orden de ejecución real (directo, o re-confirmada tras la expiración
    # porque había cupo disponible).
    assert final["estado"] == "confirmada"
