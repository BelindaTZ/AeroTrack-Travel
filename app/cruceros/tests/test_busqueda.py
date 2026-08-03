"""RF-CRU-001,002,003,004 (CU-O71,O72,O73,O74) — buscar por destino/
duración, ver itinerario/barco, comparar fechas del mismo barco.

`itinerario_puertos` real (Cruise Pricing API, confirmado en vivo) es una
lista de `{"day": N, "port": "..."}`, no strings planos — los fixtures de
abajo replican esa forma real, no la asumida originalmente."""


async def test_buscar_sin_resultados_muestra_mensaje_claro(client, naviera_factory, barco_factory, crucero_factory):
    naviera = await naviera_factory()
    barco = await barco_factory(naviera["id"])
    await crucero_factory(naviera["id"], barco["id"], itinerario_puertos=[{"day": 1, "port": "Miami, FL"}])

    resp = await client.get("/cruceros/buscar", params={"destino": "PuertoQueNoExiste9999"})
    assert resp.status_code == 200
    assert "No hay cruceros disponibles" in resp.text


async def test_buscar_por_puerto_en_itinerario(client, naviera_factory, barco_factory, crucero_factory):
    naviera = await naviera_factory(nombre="Royal Caribbean")
    barco = await barco_factory(naviera["id"], nombre="Anthem of the Seas")
    await crucero_factory(
        naviera["id"], barco["id"],
        itinerario_puertos=[{"day": 1, "port": "Miami, FL"}, {"day": 2, "port": "Nassau, Bahamas"}],
        precio_base=850.0,
    )

    resp = await client.get("/cruceros/buscar", params={"destino": "Nassau"})
    assert resp.status_code == 200
    assert "Anthem of the Seas" in resp.text
    assert "Royal Caribbean" in resp.text
    assert "$850" in resp.text


async def test_filtro_duracion_excluye_cruceros_fuera_de_rango(client, naviera_factory, barco_factory, crucero_factory):
    naviera = await naviera_factory()
    barco = await barco_factory(naviera["id"])
    await crucero_factory(naviera["id"], barco["id"], itinerario_puertos=[{"day": 1, "port": "Cozumel"}], duracion_dias=3, precio_base=300.0)
    await crucero_factory(naviera["id"], barco["id"], itinerario_puertos=[{"day": 1, "port": "Cozumel"}], duracion_dias=14, precio_base=2000.0)

    resp = await client.get("/cruceros/buscar", params={"destino": "Cozumel", "duracion_max": 7})
    assert "$300" in resp.text
    assert "$2000" not in resp.text


async def test_filtro_desde_hasta_excluye_crucero_fuera_de_rango(client, naviera_factory, barco_factory, crucero_factory):
    naviera = await naviera_factory()
    barco = await barco_factory(naviera["id"])
    await crucero_factory(
        naviera["id"], barco["id"], itinerario_puertos=[{"day": 1, "port": "Cozumel"}],
        fecha_zarpe="2027-06-15", precio_base=300.0,
    )
    await crucero_factory(
        naviera["id"], barco["id"], itinerario_puertos=[{"day": 1, "port": "Cozumel"}],
        fecha_zarpe="2027-09-01", precio_base=2000.0,
    )

    resp = await client.get("/cruceros/buscar", params={"destino": "Cozumel", "desde": "2027-06-01", "hasta": "2027-06-30"})
    assert "$300" in resp.text
    assert "$2000" not in resp.text


async def test_detalle_muestra_itinerario_y_camarotes(client, naviera_factory, barco_factory, crucero_factory, camarote_factory):
    naviera = await naviera_factory()
    barco = await barco_factory(naviera["id"], nombre="Carnival Valor")
    crucero = await crucero_factory(
        naviera["id"], barco["id"],
        itinerario_puertos=[{"day": 1, "port": "Miami, FL"}, {"day": 2, "port": "Cozumel"}],
    )
    await camarote_factory(crucero["id"], tipo_camarote="INTERIOR", precio_por_persona=700.0)
    await camarote_factory(crucero["id"], tipo_camarote="SUITE", precio_por_persona=1500.0)

    resp = await client.get(f"/cruceros/{crucero['id']}")
    assert resp.status_code == 200
    assert "Carnival Valor" in resp.text
    assert "Cozumel" in resp.text
    assert "INTERIOR" in resp.text
    assert "SUITE" in resp.text
    assert 'action="/carrito/agregar"' in resp.text


async def test_detalle_crucero_inexistente_da_404(client):
    resp = await client.get("/cruceros/id-que-no-existe")
    assert resp.status_code == 404


async def test_comparar_fechas_mismo_barco(client, naviera_factory, barco_factory, crucero_factory, camarote_factory):
    naviera = await naviera_factory()
    barco = await barco_factory(naviera["id"], nombre="Symphony of the Seas")
    c1 = await crucero_factory(naviera["id"], barco["id"], fecha_zarpe="2027-06-01", precio_base=700.0)
    c2 = await crucero_factory(naviera["id"], barco["id"], fecha_zarpe="2027-07-01", precio_base=900.0)
    await camarote_factory(c1["id"], tipo_camarote="INTERIOR", precio_por_persona=700.0)
    await camarote_factory(c2["id"], tipo_camarote="INTERIOR", precio_por_persona=900.0)

    resp = await client.get(f"/cruceros/barco/{barco['id']}/fechas")
    assert resp.status_code == 200
    assert "Symphony of the Seas" in resp.text
    assert "2027-06-01" in resp.text
    assert "2027-07-01" in resp.text


async def test_comparar_fechas_barco_inexistente_da_404(client):
    resp = await client.get("/cruceros/barco/id-que-no-existe/fechas")
    assert resp.status_code == 404
