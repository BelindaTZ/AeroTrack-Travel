"""RF-HOT-001,002,003,006,007 (CU-O54,O55,O56,O57,O58) — buscar, detalle
con reseñas/tarifas y filtrar."""


async def test_buscar_sin_resultados_muestra_mensaje_claro(client):
    resp = await client.get("/hoteles/buscar", params={"ciudad": "CiudadInexistente9999"})
    assert resp.status_code == 200
    assert "No hay hoteles disponibles" in resp.text


async def test_buscar_con_resultados_muestra_precio_desde(client, hotel_factory, tarifa_hotel_factory):
    hotel = await hotel_factory(ciudad="Madrid", nombre="Hotel Prado")
    await tarifa_hotel_factory(hotel["id"], precio_final=150.0)
    await tarifa_hotel_factory(hotel["id"], precio_final=90.0)

    resp = await client.get("/hoteles/buscar", params={"ciudad": "Madrid"})
    assert resp.status_code == 200
    assert "Hotel Prado" in resp.text
    assert "$90" in resp.text  # precio_desde = mínimo de las tarifas


async def test_filtro_estrellas_minimas(client, hotel_factory):
    await hotel_factory(ciudad="Miami", nombre="Cinco Estrellas", estrellas=5)
    await hotel_factory(ciudad="Miami", nombre="Tres Estrellas", estrellas=3)

    resp = await client.get("/hoteles/buscar", params={"ciudad": "Miami", "estrellas_min": 4})
    assert "Cinco Estrellas" in resp.text
    assert "Tres Estrellas" not in resp.text


async def test_filtro_precio_maximo(client, hotel_factory, tarifa_hotel_factory):
    barato = await hotel_factory(ciudad="Roma", nombre="Barato")
    await tarifa_hotel_factory(barato["id"], precio_final=50.0)
    caro = await hotel_factory(ciudad="Roma", nombre="Caro")
    await tarifa_hotel_factory(caro["id"], precio_final=500.0)

    resp = await client.get("/hoteles/buscar", params={"ciudad": "Roma", "precio_max": 100})
    assert "Barato" in resp.text
    assert "Caro" not in resp.text


async def test_detalle_muestra_tarifas_reembolsable_y_no_reembolsable(client, hotel_factory, tarifa_hotel_factory):
    hotel = await hotel_factory(ciudad="Paris", nombre="Hilton Paris Opera")
    await tarifa_hotel_factory(hotel["id"], tipo_habitacion="Standard", precio_final=120.0, reembolsable=True)
    await tarifa_hotel_factory(hotel["id"], tipo_habitacion="Non-Refundable Deal", precio_final=95.0, reembolsable=False)

    resp = await client.get(f"/hoteles/{hotel['id']}")
    assert resp.status_code == 200
    assert "Hilton Paris Opera" in resp.text
    assert "Reembolsable" in resp.text
    assert "No reembolsable" in resp.text
    assert 'action="/carrito/agregar"' in resp.text


async def test_detalle_muestra_resenas(client, hotel_factory, resena_hotel_factory):
    hotel = await hotel_factory(ciudad="Paris", nombre="Hotel con Reseñas")
    await resena_hotel_factory(hotel["id"], autor="Carlos", comentario="Muy limpio y céntrico")

    resp = await client.get(f"/hoteles/{hotel['id']}")
    assert "Carlos" in resp.text
    assert "Muy limpio y céntrico" in resp.text


async def test_tarifa_sin_cupo_no_ofrece_agregar(client, hotel_factory, tarifa_hotel_factory):
    hotel = await hotel_factory(ciudad="Paris", nombre="Hotel Sin Cupo")
    await tarifa_hotel_factory(hotel["id"], tipo_habitacion="Agotada", cupos_disponibles=0)

    resp = await client.get(f"/hoteles/{hotel['id']}")
    assert "Sin cupo" in resp.text


async def test_detalle_hotel_inexistente_da_404(client):
    resp = await client.get("/hoteles/id-que-no-existe")
    assert resp.status_code == 404
