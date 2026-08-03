"""RF-HOT-009 (CU-O60) — la modalidad de pago elegida al agregar un ítem
de hotel al carrito debe sobrevivir hasta `reserva_items` en el checkout,
para que Facturación (RF-FAC-012) sepa si debe cobrar de inmediato o
autorizar y esperar captura."""

from app.carrito.services.carrito_service import agregar_item, confirmar_checkout
from app.shared import minio_operational_client as moc


async def _crear_hotel_con_tarifa(pb, precio_final: float = 120.0):
    hotel = await pb.create_record(
        "hoteles_catalogo",
        {
            "nombre": "Hotel Prueba Modalidad Pago", "direccion": "1 Rue de Test", "ciudad": "Paris", "pais": "France",
            "estrellas": 4, "calificacion_promedio": 4.5, "cantidad_resenas": 20,
            "descripcion_corta": "", "descripcion": "Descripción de prueba.",
            "servicios": [], "hora_checkin": "15:00", "hora_checkout": "11:00",
            "imagen_principal": "", "fuente_entity_url": "test-modalidad-pago",
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        },
    )
    tarifa = await pb.create_record(
        "hoteles_tarifas",
        {
            "hotel_id": hotel["id"], "tipo_habitacion": "Standard Room", "bed_type": "1 King Bed",
            "max_ocupantes": 2, "desayuno_incluido": False, "precio_final": precio_final, "moneda": "USD",
            "reembolsable": True, "cupos_disponibles": 3, "pago_diferido_disponible": True,
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        },
    )
    return hotel, tarifa


async def test_agregar_item_con_modalidad_pago_diferido_persiste(pasajero_factory, pb):
    _, pasajero = await pasajero_factory()
    hotel, tarifa = await _crear_hotel_con_tarifa(pb)

    try:
        item = await agregar_item(
            pasajero["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": tarifa["id"]},
            precio_snapshot=120.0, modalidad_pago="pago_diferido",
        )
        assert item["modalidad_pago"] == "pago_diferido"
        carrito_id = item["carrito_id"]
        await moc.eliminar("carrito_items", item["id"])
        await moc.eliminar("carritos", carrito_id)
    finally:
        await pb.delete_record("hoteles_tarifas", tarifa["id"])
        await pb.delete_record("hoteles_catalogo", hotel["id"])


async def test_agregar_item_sin_modalidad_pago_no_la_fija(pasajero_factory, pb):
    _, pasajero = await pasajero_factory()
    hotel, tarifa = await _crear_hotel_con_tarifa(pb)

    try:
        item = await agregar_item(
            pasajero["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": tarifa["id"]},
            precio_snapshot=120.0,
        )
        assert not item.get("modalidad_pago")
        carrito_id = item["carrito_id"]
        await moc.eliminar("carrito_items", item["id"])
        await moc.eliminar("carritos", carrito_id)
    finally:
        await pb.delete_record("hoteles_tarifas", tarifa["id"])
        await pb.delete_record("hoteles_catalogo", hotel["id"])


async def test_checkout_copia_modalidad_pago_a_reserva_items(pasajero_factory, pb):
    _, pasajero = await pasajero_factory()
    hotel, tarifa = await _crear_hotel_con_tarifa(pb)

    try:
        await agregar_item(
            pasajero["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": tarifa["id"]},
            precio_snapshot=120.0, modalidad_pago="pago_diferido",
        )
        reserva = await confirmar_checkout(pasajero["id"])

        items = await moc.listar_todos("reserva_items")
        items = [i for i in items if i.get("reserva_id") == reserva["id"]]
        assert len(items) == 1
        assert items[0]["modalidad_pago"] == "pago_diferido"

        for i in items:
            await moc.eliminar("reserva_items", i["id"])
        await moc.eliminar("reservas", reserva["id"])
    finally:
        await pb.delete_record("hoteles_tarifas", tarifa["id"])
        await pb.delete_record("hoteles_catalogo", hotel["id"])
