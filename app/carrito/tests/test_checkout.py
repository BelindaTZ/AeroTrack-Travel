"""RF-CAR-004 (CU-O96) — checkout con revalidación (RN-CAR-001) y
conversión 1:1 a `reserva_items`."""

import datetime

from app.carrito.repositories.carrito_repo import CarritoRepository
from app.carrito.services.carrito_service import CarritoVacio, agregar_item, confirmar_checkout, revalidar_precios
from app.shared import minio_operational_client as moc


async def _crear_hotel_con_tarifa(pb, precio_final: float = 300.0) -> tuple[dict, dict]:
    ahora = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z")
    hotel = await pb.create_record(
        "hoteles_catalogo",
        {
            "nombre": "Hotel de Prueba Carrito",
            "direccion": "1 Test St",
            "ciudad": "Paris",
            "pais": "FR",
            "fecha_actualizacion": ahora,
        },
    )
    tarifa = await pb.create_record(
        "hoteles_tarifas",
        {
            "hotel_id": hotel["id"],
            "tipo_habitacion": "Standard",
            "precio_final": precio_final,
            "moneda": "USD",
            "reembolsable": False,
            "cupos_disponibles": 5,
            "fecha_actualizacion": ahora,
        },
    )
    return hotel, tarifa


async def test_revalidar_precios_detecta_cambio_real(pb, pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=100.0)

    item = await agregar_item(pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa["id"]}, 100.0)

    # El precio real subió después de agregarlo al carrito.
    await pb.update_record("tarifas_vuelo", tarifa["id"], {"precio_final": 120.0})

    resultado = await revalidar_precios(pasajero["id"])
    assert len(resultado["cambios"]) == 1
    assert resultado["cambios"][0]["precio_snapshot"] == 100.0
    assert resultado["cambios"][0]["precio_vigente"] == 120.0

    carrito = await CarritoRepository().carrito_de_trabajo(pasajero["id"])
    await moc.eliminar("carrito_items", item["id"])
    await moc.eliminar("carritos", carrito["id"])


async def test_confirmar_checkout_vacio_rechaza(pasajero_factory):
    _usuario, pasajero = await pasajero_factory()
    try:
        await confirmar_checkout(pasajero["id"])
        raise AssertionError("debía lanzar CarritoVacio")
    except CarritoVacio:
        pass


async def test_confirmar_checkout_un_solo_tipo_no_es_paquete(pb, pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=100.0)

    item = await agregar_item(pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa["id"]}, 100.0)
    carrito_id = item["carrito_id"]

    reserva = await confirmar_checkout(pasajero["id"])
    assert reserva["es_paquete"] is False
    assert reserva["total_pagar"] == 100.0
    assert reserva["estado"] == "pendiente_pago"

    carrito = await moc.obtener("carritos", carrito_id)
    assert carrito["estado"] == "convertido"

    reserva_items = await moc.listar_todos("reserva_items")
    reserva_items = [i for i in reserva_items if i.get("reserva_id") == reserva["id"]]
    assert len(reserva_items) == 1
    assert reserva_items[0]["tipo_producto"] == "vuelo"

    for ri in reserva_items:
        await moc.eliminar("reserva_items", ri["id"])
    await moc.eliminar("reservas", reserva["id"])
    # el item del carrito NO se borra por el checkout — el carrito queda
    # 'convertido' como historial; hay que borrar el ítem antes que el
    # carrito (relación requerida) — solo por higiene de la prueba.
    items_restantes = await moc.listar_todos("carrito_items")
    for ci in [i for i in items_restantes if i.get("carrito_id") == carrito_id]:
        await moc.eliminar("carrito_items", ci["id"])
    await moc.eliminar("carritos", carrito_id)


async def test_confirmar_checkout_multi_tipo_es_paquete_y_usa_precio_vigente(
    pb, pasajero_factory, vuelo_factory, tarifa_factory
):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=100.0)
    hotel, hotel_tarifa = await _crear_hotel_con_tarifa(pb, precio_final=300.0)

    await agregar_item(pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa["id"]}, 100.0)
    item_hotel = await agregar_item(
        pasajero["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": hotel_tarifa["id"]}, 250.0  # snapshot viejo
    )
    carrito_id = item_hotel["carrito_id"]

    reserva = await confirmar_checkout(pasajero["id"])
    assert reserva["es_paquete"] is True  # 2 tipo_producto distintos (vuelo + hotel)
    # usa el precio VIGENTE de hoteles_tarifas (300.0), no el snapshot viejo (250.0)
    assert reserva["total_pagar"] == 400.0

    reserva_items = await moc.listar_todos("reserva_items")
    reserva_items = [i for i in reserva_items if i.get("reserva_id") == reserva["id"]]
    assert len(reserva_items) == 2
    item_hotel_confirmado = next(ri for ri in reserva_items if ri["tipo_producto"] == "hotel")
    assert item_hotel_confirmado["precio_final"] == 300.0

    for ri in reserva_items:
        await moc.eliminar("reserva_items", ri["id"])
    await moc.eliminar("reservas", reserva["id"])
    items_restantes = await moc.listar_todos("carrito_items")
    for ci in [i for i in items_restantes if i.get("carrito_id") == carrito_id]:
        await moc.eliminar("carrito_items", ci["id"])
    await moc.eliminar("carritos", carrito_id)
    await pb.delete_record("hoteles_tarifas", hotel_tarifa["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])
