"""RF-AUT-001,002,003 (CU-O61,O62,O63) — buscar, ver detalle y filtrar."""


async def test_buscar_sin_resultados_muestra_mensaje_claro(client):
    resp = await client.get("/autos/buscar", params={"ciudad": "CiudadInexistente9999"})
    assert resp.status_code == 200
    assert "No hay autos disponibles" in resp.text


async def test_buscar_con_resultados_muestra_auto(client, auto_factory):
    auto = await auto_factory(ciudad_recogida="Madrid", modelo="Peugeot 3008", precio_dia=80.0)

    resp = await client.get("/autos/buscar", params={"ciudad": "Madrid"})
    assert resp.status_code == 200
    assert "Peugeot 3008" in resp.text
    assert "$80" in resp.text


async def test_buscar_es_insensible_a_mayusculas(client, auto_factory):
    await auto_factory(ciudad_recogida="Paris", modelo="VW T-Roc")

    resp = await client.get("/autos/buscar", params={"ciudad": "paris"})
    assert resp.status_code == 200
    assert "VW T-Roc" in resp.text


async def test_filtro_categoria_instantaneo_sin_boton_aplicar(client, auto_factory):
    await auto_factory(ciudad_recogida="New York", categoria="SUV")

    resp = await client.get("/autos/buscar", params={"ciudad": "New York"})
    html = resp.text
    assert "setFiltro" in html
    assert ">Aplicar<" not in html
    assert 'id="form-busqueda-autos"' in html


async def test_filtro_precio_maximo_excluye_ofertas_caras(client, auto_factory):
    await auto_factory(ciudad_recogida="Miami", modelo="Barato", precio_dia=40.0)
    await auto_factory(ciudad_recogida="Miami", modelo="Caro", precio_dia=200.0)

    resp = await client.get("/autos/buscar", params={"ciudad": "Miami", "precio_max": 50})
    assert "Barato" in resp.text
    assert "Caro" not in resp.text


async def test_detalle_muestra_especificaciones(client, auto_factory):
    auto = await auto_factory(ciudad_recogida="Paris", modelo="BMW X1", transmision="Manual")

    resp = await client.get(f"/autos/{auto['id']}")
    assert resp.status_code == 200
    assert "BMW X1" in resp.text
    assert "Manual" in resp.text
    assert 'action="/carrito/agregar"' in resp.text


async def test_detalle_auto_inexistente_da_404(client):
    resp = await client.get("/autos/id-que-no-existe")
    assert resp.status_code == 404
