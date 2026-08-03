"""RF-HOT-004/005 (CU-O118) — generación de catálogo vía flujo de 3 pasos
de HotelLens, con doble determinista (ver conftest.py)."""

from app.hoteles.services.catalogo_service import generar_catalogo

HOTEL_BUSQUEDA = {
    "name": "Hotel de Prueba París",
    "url": "https://www.google.com/travel/hotels/entity/test123",
    "image_url": "https://example.com/foto.jpg",
    "stars": 4,
    "rating": 4.5,
    "reviews": 1200,
}

OFERTA_CON_BOOKING = {
    "provider": "Booking.com",
    "booking_url": "https://booking.com/hotel?dest_id=721193&highlighted_hotels=721193&show_room=1",
}

DETALLE_BOOKING = {
    "city": "Paris",
    "country_code": "FR",
    "address": "1 Rue de Test",
    "latitude": 48.85,
    "longitude": 2.35,
    "amenities": ["wifi", "piscina"],
    "category_scores": {"Value": 8.5, "Location": 9.0, "Rooms": 8.0, "Cleanliness": 9.2, "Service": 8.8},
    "summary": "Hotel céntrico de prueba",
    "check_in_time": "15:00",
    "check_out_time": "11:00",
    "room_offers": [
        {
            "room_name": "Classic Double or Twin Room",
            "bed_type": "1 cama doble",
            "max_occupancy": 2,
            "room_size_m2": 22,
            "breakfast_included": True,
            "total_price": 134.0,
            "currency": "USD",
            "free_cancellation": True,
            "refundable_until": "2027-06-14",
            "rooms_left": 6,
        }
    ],
}

RESENAS = [
    {"author": "Ana", "rating": 5, "rating_scale": 5, "text": "Excelente", "relative_date": "hace 2 meses", "source": "Google"},
]


async def test_generar_catalogo_crea_hotel_tarifa_y_resena(pb, hotellens_falso):
    cliente = hotellens_falso(
        resultados_busqueda={"Paris": [HOTEL_BUSQUEDA]},
        ofertas={HOTEL_BUSQUEDA["url"]: [OFERTA_CON_BOOKING]},
        detalles={"721193": DETALLE_BOOKING},
        resenas={HOTEL_BUSQUEDA["url"]: RESENAS},
    )

    resumen = await generar_catalogo(cliente, ciudades=["Paris"], max_hoteles_por_ciudad=1)
    assert resumen["procesados"] == 1
    assert resumen["resueltos"] == 1
    assert resumen["estado"] == "exitoso"

    hotel = await pb.get_first("hoteles_catalogo", f'fuente_entity_url="{HOTEL_BUSQUEDA["url"]}"')
    assert hotel is not None
    assert hotel["ciudad"] == "Paris"
    assert hotel["pais"] == "FR"

    tarifas = await pb.list_records("hoteles_tarifas", {"filter": f'hotel_id="{hotel["id"]}"'})
    assert tarifas["totalItems"] == 1
    tarifa = tarifas["items"][0]
    assert tarifa["precio_final"] == 134.0
    assert tarifa["cupos_disponibles"] == 6  # RN-HOT-001: cupo real, no aproximado
    assert tarifa["reembolsable"] is True
    assert tarifa["pago_diferido_disponible"] is True  # RN-HOT-004: sintético, atado a reembolsable

    resenas = await pb.list_records("hoteles_resenas", {"filter": f'hotel_id="{hotel["id"]}"'})
    assert resenas["totalItems"] == 1
    assert resenas["items"][0]["autor"] == "Ana"

    log = await pb.get_first(
        "sincronizaciones_log", f'tipo_producto="hotel" && estado="exitoso"'
    )
    assert log is not None

    # limpieza — hoteles_disponibilidad ANTES que hoteles_tarifas (relation
    # required, ver pb_schema_hoteles.py; generar_catalogo ahora también
    # crea filas de disponibilidad por noche, RF-HOT-004)
    disponibilidad = await pb.list_records("hoteles_disponibilidad", {"filter": f'hotel_id="{hotel["id"]}"', "perPage": 200})
    for d in disponibilidad["items"]:
        await pb.delete_record("hoteles_disponibilidad", d["id"])
    for r in resenas["items"]:
        await pb.delete_record("hoteles_resenas", r["id"])
    for t in tarifas["items"]:
        await pb.delete_record("hoteles_tarifas", t["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_es_idempotente_no_duplica_hotel(pb, hotellens_falso):
    cliente = hotellens_falso(
        resultados_busqueda={"Paris": [HOTEL_BUSQUEDA]},
        ofertas={HOTEL_BUSQUEDA["url"]: [OFERTA_CON_BOOKING]},
        detalles={"721193": DETALLE_BOOKING},
        resenas={HOTEL_BUSQUEDA["url"]: RESENAS},
    )

    await generar_catalogo(cliente, ciudades=["Paris"], max_hoteles_por_ciudad=1)
    await generar_catalogo(cliente, ciudades=["Paris"], max_hoteles_por_ciudad=1)

    hoteles = await pb.list_records(
        "hoteles_catalogo", {"filter": f'fuente_entity_url="{HOTEL_BUSQUEDA["url"]}"'}
    )
    assert hoteles["totalItems"] == 1  # segunda corrida actualiza, no duplica
    hotel = hoteles["items"][0]

    tarifas = await pb.list_records("hoteles_tarifas", {"filter": f'hotel_id="{hotel["id"]}"'})
    assert tarifas["totalItems"] == 1  # tarifas se reemplazan, no se acumulan (RN-HOT-001)

    # limpieza — hoteles_disponibilidad ANTES que hoteles_tarifas (relation
    # required, ver pb_schema_hoteles.py)
    disponibilidad = await pb.list_records("hoteles_disponibilidad", {"filter": f'hotel_id="{hotel["id"]}"', "perPage": 200})
    for d in disponibilidad["items"]:
        await pb.delete_record("hoteles_disponibilidad", d["id"])
    resenas = await pb.list_records("hoteles_resenas", {"filter": f'hotel_id="{hotel["id"]}"'})
    for r in resenas["items"]:
        await pb.delete_record("hoteles_resenas", r["id"])
    for t in tarifas["items"]:
        await pb.delete_record("hoteles_tarifas", t["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])
    logs = await pb.list_records(
        "sincronizaciones_log", {"filter": f'tipo_producto="hotel"', "sort": "-created", "perPage": 5}
    )
    for log in logs["items"][:2]:
        await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_sin_oferta_booking_no_crea_hotel(pb, hotellens_falso):
    """Un resultado de Google Hotels sin ningún booking_url resoluble a
    hotel_id de Booking.com no es un error — algunos resultados no tienen
    match en Booking.com. Se cuenta como procesado pero no resuelto."""
    cliente = hotellens_falso(
        resultados_busqueda={"Paris": [HOTEL_BUSQUEDA]},
        ofertas={HOTEL_BUSQUEDA["url"]: [{"provider": "Agoda", "booking_url": "https://agoda.com/sin-id-de-booking"}]},
    )

    resumen = await generar_catalogo(cliente, ciudades=["Paris"], max_hoteles_por_ciudad=1)
    assert resumen["procesados"] == 1
    assert resumen["resueltos"] == 0
    assert resumen["estado"] == "parcial"

    hotel = await pb.get_first("hoteles_catalogo", f'fuente_entity_url="{HOTEL_BUSQUEDA["url"]}"')
    assert hotel is None

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="hotel" && estado="parcial"')
    assert log is not None
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_falla_completa_queda_registrada_como_fallido(pb, hotellens_falso):
    class ClienteQueFalla(hotellens_falso):
        async def buscar_hoteles(self, ciudad: str) -> list[dict]:
            raise ConnectionError("HotelLens no disponible (doble de prueba)")

    resumen = await generar_catalogo(ClienteQueFalla(), ciudades=["Paris"], max_hoteles_por_ciudad=1)
    assert resumen["estado"] == "fallido"
    assert "no disponible" in resumen["error_detalle"]

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="hotel" && estado="fallido"')
    assert log is not None
    assert log["error_detalle"]
    await pb.delete_record("sincronizaciones_log", log["id"])
