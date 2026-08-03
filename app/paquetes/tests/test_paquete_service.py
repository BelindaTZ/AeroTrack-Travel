"""RF-PAQ-001-005 (CU-O76-O80) — construcción de paquete, desglose de
ahorro (RN-PAQ-004: el descuento nunca reduce el precio real de cada
componente), confirmación (RN-PAQ-001/002), traslado aeropuerto, y
condiciones reales por componente (RF-PAQ-004)."""

import datetime

from app.paquetes.services.paquete_service import (
    ComponenteObligatorioFaltante,
    SinPermiso,
    agregar_componente,
    agregar_traslado_aeropuerto,
    calcular_resumen,
    cambiar_componente,
    condiciones_por_componente,
    confirmar_paquete,
    iniciar_paquete,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc


async def _crear_hotel_con_tarifa(pb, precio_final: float = 300.0, reembolsable: bool = True) -> tuple[dict, dict]:
    ahora = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z")
    hotel = await pb.create_record(
        "hoteles_catalogo",
        {"nombre": "Hotel de Prueba Paquetes", "direccion": "1 Test St", "ciudad": "Paris", "pais": "FR", "fecha_actualizacion": ahora},
    )
    tarifa = await pb.create_record(
        "hoteles_tarifas",
        {
            "hotel_id": hotel["id"],
            "tipo_habitacion": "Standard",
            "precio_final": precio_final,
            "moneda": "USD",
            "reembolsable": reembolsable,
            "cancelacion_hasta": "2027-01-01 00:00:00.000Z",
            "cupos_disponibles": 10,
            "fecha_actualizacion": ahora,
        },
    )
    return hotel, tarifa


async def _limpiar_reserva(reserva_id: str) -> None:
    repo = ReservasRepository()
    for item in await repo.items_de_reserva(reserva_id):
        await moc.eliminar("reserva_items", item["id"])
    for extra in await repo.extras_de_reserva(reserva_id):
        await moc.eliminar("reserva_extras", extra["id"])
    await moc.eliminar("reservas", reserva_id)


async def test_iniciar_paquete_crea_reserva_con_un_solo_item(pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)

    reserva = await iniciar_paquete(pasajero["id"], vuelo["id"], tarifa["id"], 200.0)
    assert reserva["es_paquete"] is False
    assert reserva["total_pagar"] == 200.0

    items = await ReservasRepository().items_de_reserva(reserva["id"])
    assert len(items) == 1
    assert items[0]["tipo_producto"] == "vuelo"

    await _limpiar_reserva(reserva["id"])


async def test_agregar_hotel_activa_es_paquete_y_recalcula_total(pb, pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)
    hotel, hotel_tarifa = await _crear_hotel_con_tarifa(pb, precio_final=300.0)

    reserva = await iniciar_paquete(pasajero["id"], vuelo["id"], tarifa["id"], 200.0)
    await agregar_componente(
        pasajero["id"], reserva["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": hotel_tarifa["id"]}, 300.0
    )

    actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert actualizada["es_paquete"] is True
    assert actualizada["total_pagar"] == 500.0  # sin descuento todavía, se aplica al confirmar

    await _limpiar_reserva(reserva["id"])
    await pb.delete_record("hoteles_tarifas", hotel_tarifa["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])


async def test_calcular_resumen_desglosa_ahorro_vuelo_hotel(pb, pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)
    hotel, hotel_tarifa = await _crear_hotel_con_tarifa(pb, precio_final=300.0)

    reserva = await iniciar_paquete(pasajero["id"], vuelo["id"], tarifa["id"], 200.0)
    await agregar_componente(
        pasajero["id"], reserva["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": hotel_tarifa["id"]}, 300.0
    )

    resumen = await calcular_resumen(reserva["id"])
    assert resumen["combinacion"] == "vuelo+hotel"
    assert resumen["subtotal"] == 500.0
    assert resumen["porcentaje_descuento"] == 10.0  # sembrado en tipos_paquete_descuento
    assert resumen["monto_descuento"] == 50.0
    assert resumen["precio_final_paquete"] == 450.0
    assert len(resumen["componentes"]) == 2
    # RN-PAQ-004: cada componente conserva su precio real, el descuento
    # nunca se reparte/oculta dentro de cada línea.
    assert {c["precio_final"] for c in resumen["componentes"]} == {200.0, 300.0}

    await _limpiar_reserva(reserva["id"])
    await pb.delete_record("hoteles_tarifas", hotel_tarifa["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])


async def test_confirmar_paquete_copia_descuento_y_aplica_precio_final(
    pb, pasajero_factory, vuelo_factory, tarifa_factory
):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)
    hotel, hotel_tarifa = await _crear_hotel_con_tarifa(pb, precio_final=300.0)

    reserva = await iniciar_paquete(pasajero["id"], vuelo["id"], tarifa["id"], 200.0)
    await agregar_componente(
        pasajero["id"], reserva["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": hotel_tarifa["id"]}, 300.0
    )

    confirmada = await confirmar_paquete(pasajero["id"], reserva["id"])
    assert confirmada["descuento_paquete_pct"] == 10.0
    assert confirmada["total_pagar"] == 450.0

    # Los componentes individuales conservan su precio real (RN-PAQ-004) —
    # el descuento vive solo en la cabecera, nunca en reserva_items.
    items = await ReservasRepository().items_de_reserva(reserva["id"])
    assert {i["precio_final"] for i in items} == {200.0, 300.0}

    await _limpiar_reserva(reserva["id"])
    await pb.delete_record("hoteles_tarifas", hotel_tarifa["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])


async def test_confirmar_paquete_sin_hotel_rechaza(pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)

    reserva = await iniciar_paquete(pasajero["id"], vuelo["id"], tarifa["id"], 200.0)

    try:
        await confirmar_paquete(pasajero["id"], reserva["id"])
        raise AssertionError("debía lanzar ComponenteObligatorioFaltante")
    except ComponenteObligatorioFaltante as exc:
        assert "hotel" in exc.faltantes

    await _limpiar_reserva(reserva["id"])


async def test_cambiar_componente_no_afecta_los_demas(pb, pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)
    hotel_a, tarifa_a = await _crear_hotel_con_tarifa(pb, precio_final=300.0)
    hotel_b, tarifa_b = await _crear_hotel_con_tarifa(pb, precio_final=350.0)

    reserva = await iniciar_paquete(pasajero["id"], vuelo["id"], tarifa["id"], 200.0)
    item_hotel = await agregar_componente(
        pasajero["id"], reserva["id"], "hotel", {"hotel_id": hotel_a["id"], "hotel_tarifa_id": tarifa_a["id"]}, 300.0
    )

    await cambiar_componente(
        pasajero["id"], reserva["id"], item_hotel["id"], {"hotel_id": hotel_b["id"], "hotel_tarifa_id": tarifa_b["id"]}, 350.0
    )

    items = await ReservasRepository().items_de_reserva(reserva["id"])
    assert len(items) == 2  # sigue siendo vuelo + hotel, no se duplicó ni se perdió el vuelo
    hotel_actualizado = next(i for i in items if i["tipo_producto"] == "hotel")
    assert hotel_actualizado["hotel_id"] == hotel_b["id"]
    assert hotel_actualizado["precio_final"] == 350.0

    actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert actualizada["total_pagar"] == 550.0  # 200 + 350

    await _limpiar_reserva(reserva["id"])
    for h, t in [(hotel_a, tarifa_a), (hotel_b, tarifa_b)]:
        await pb.delete_record("hoteles_tarifas", t["id"])
        await pb.delete_record("hoteles_catalogo", h["id"])


async def test_agregar_traslado_aeropuerto(pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)

    reserva = await iniciar_paquete(pasajero["id"], vuelo["id"], tarifa["id"], 200.0)
    extra = await agregar_traslado_aeropuerto(pasajero["id"], reserva["id"], "Traslado hotel-aeropuerto", 25.0)

    assert extra["tipo"] == "traslado_aeropuerto"
    assert extra["precio"] == 25.0

    await _limpiar_reserva(reserva["id"])


async def test_condiciones_por_componente_trae_datos_reales(pb, pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)
    hotel, hotel_tarifa = await _crear_hotel_con_tarifa(pb, precio_final=300.0, reembolsable=True)

    reserva = await iniciar_paquete(pasajero["id"], vuelo["id"], tarifa["id"], 200.0)
    await agregar_componente(
        pasajero["id"], reserva["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": hotel_tarifa["id"]}, 300.0
    )

    condiciones = await condiciones_por_componente(reserva["id"])
    assert len(condiciones) == 2
    cond_vuelo = next(c for c in condiciones if c["tipo_producto"] == "vuelo")
    cond_hotel = next(c for c in condiciones if c["tipo_producto"] == "hotel")
    assert cond_vuelo["condiciones"] is not None  # política real vía niveles_tarifa
    assert cond_hotel["condiciones"]["reembolsable"] is True  # dato real de hoteles_tarifas, no una política inventada

    await _limpiar_reserva(reserva["id"])
    await pb.delete_record("hoteles_tarifas", hotel_tarifa["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])


async def test_agregar_componente_de_reserva_ajena_rechaza(pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario_a, pasajero_a = await pasajero_factory()
    _usuario_b, pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)

    reserva = await iniciar_paquete(pasajero_a["id"], vuelo["id"], tarifa["id"], 200.0)

    try:
        await agregar_componente(pasajero_b["id"], reserva["id"], "hotel", {}, 300.0)
        raise AssertionError("debía lanzar SinPermiso")
    except SinPermiso:
        pass

    await _limpiar_reserva(reserva["id"])
