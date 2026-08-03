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


async def test_buscar_con_fechas_excluye_hotel_con_noche_sin_cupo(
    client, hotel_factory, tarifa_hotel_factory, disponibilidad_hotel_factory
):
    """RF-HOT-004 — un hotel cuya única tarifa se queda sin cupo en UNA
    noche del rango pedido se excluye del listado entero, aunque la otra
    noche sí tenga cupo (nunca se ofrece una estadía con noches parciales)."""
    hotel = await hotel_factory(ciudad="Lima", nombre="Hotel Con Hueco")
    tarifa = await tarifa_hotel_factory(hotel["id"], precio_final=80.0)
    await disponibilidad_hotel_factory(hotel["id"], tarifa["id"], "2027-07-01", cupos_disponibles=5)
    await disponibilidad_hotel_factory(hotel["id"], tarifa["id"], "2027-07-02", cupos_disponibles=0)  # agotada

    resp = await client.get(
        "/hoteles/buscar", params={"ciudad": "Lima", "checkin": "2027-07-01", "checkout": "2027-07-03"}
    )
    assert resp.status_code == 200
    assert "Hotel Con Hueco" not in resp.text


async def test_buscar_con_fechas_respeta_habitaciones_solicitadas(
    client, hotel_factory, tarifa_hotel_factory, disponibilidad_hotel_factory
):
    """RF-HOT-004 — pedir más habitaciones de las que el cupo mínimo del
    rango permite excluye la tarifa (y el hotel, si es su única tarifa)."""
    hotel = await hotel_factory(ciudad="Quito", nombre="Hotel Pocas Habitaciones")
    tarifa = await tarifa_hotel_factory(hotel["id"], precio_final=70.0)
    await disponibilidad_hotel_factory(hotel["id"], tarifa["id"], "2027-07-10", cupos_disponibles=2)
    await disponibilidad_hotel_factory(hotel["id"], tarifa["id"], "2027-07-11", cupos_disponibles=2)

    resp_ok = await client.get(
        "/hoteles/buscar",
        params={"ciudad": "Quito", "checkin": "2027-07-10", "checkout": "2027-07-12", "habitaciones": 2},
    )
    assert "Hotel Pocas Habitaciones" in resp_ok.text

    resp_excede = await client.get(
        "/hoteles/buscar",
        params={"ciudad": "Quito", "checkin": "2027-07-10", "checkout": "2027-07-12", "habitaciones": 3},
    )
    assert "Hotel Pocas Habitaciones" not in resp_excede.text


async def test_detalle_con_fechas_muestra_precio_total_por_noches(
    client, hotel_factory, tarifa_hotel_factory, disponibilidad_hotel_factory
):
    hotel = await hotel_factory(ciudad="Cusco", nombre="Hotel Precio Total")
    tarifa = await tarifa_hotel_factory(hotel["id"], precio_final=50.0)
    await disponibilidad_hotel_factory(hotel["id"], tarifa["id"], "2027-07-20", cupos_disponibles=5)
    await disponibilidad_hotel_factory(hotel["id"], tarifa["id"], "2027-07-21", cupos_disponibles=5)
    await disponibilidad_hotel_factory(hotel["id"], tarifa["id"], "2027-07-22", cupos_disponibles=5)

    resp = await client.get(
        f"/hoteles/{hotel['id']}", params={"checkin": "2027-07-20", "checkout": "2027-07-23"}
    )
    assert resp.status_code == 200
    assert "$150.00" in resp.text  # 50.0/noche * 3 noches, no $50 plano como antes del fix


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


async def test_detalle_muestra_tarifas_reembolsable_y_no_reembolsable(
    client, hotel_factory, tarifa_hotel_factory, disponibilidad_hotel_factory
):
    hotel = await hotel_factory(ciudad="Paris", nombre="Hilton Paris Opera")
    t1 = await tarifa_hotel_factory(hotel["id"], tipo_habitacion="Standard", precio_final=120.0, reembolsable=True)
    t2 = await tarifa_hotel_factory(hotel["id"], tipo_habitacion="Non-Refundable Deal", precio_final=95.0, reembolsable=False)
    # RF-HOT-004 — con fechas seleccionadas se necesita cupo real por
    # noche (checkin=06-01, checkout=06-03 -> noches 06-01 y 06-02).
    for t in (t1, t2):
        await disponibilidad_hotel_factory(hotel["id"], t["id"], "2027-06-01")
        await disponibilidad_hotel_factory(hotel["id"], t["id"], "2027-06-02")

    resp = await client.get(f"/hoteles/{hotel['id']}", params={"checkin": "2027-06-01", "checkout": "2027-06-03"})
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


async def test_tarifa_sin_cupo_no_ofrece_agregar(
    client, hotel_factory, tarifa_hotel_factory, disponibilidad_hotel_factory
):
    hotel = await hotel_factory(ciudad="Paris", nombre="Hotel Sin Cupo")
    tarifa = await tarifa_hotel_factory(hotel["id"], tipo_habitacion="Agotada", cupos_disponibles=0)
    await disponibilidad_hotel_factory(hotel["id"], tarifa["id"], "2027-06-01", cupos_disponibles=0)
    await disponibilidad_hotel_factory(hotel["id"], tarifa["id"], "2027-06-02", cupos_disponibles=0)

    resp = await client.get(f"/hoteles/{hotel['id']}", params={"checkin": "2027-06-01", "checkout": "2027-06-03"})
    assert "Sin cupo" in resp.text


async def test_detalle_hotel_inexistente_da_404(client):
    resp = await client.get("/hoteles/id-que-no-existe")
    assert resp.status_code == 404
