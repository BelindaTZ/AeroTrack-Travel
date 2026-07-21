from app.vuelos.repositories.dims_reader import resolver_aeropuerto


# ── CU-O17 / RF-VUE-001 (CHK001, CHK002) ──────────────────────────────────

async def test_buscar_sin_resultados_muestra_mensaje_claro(client):
    resp = await client.get(
        "/vuelos/buscar",
        params={"origen": "JFK", "destino": "LAX", "fecha": "2099-01-01", "pasajeros": 1},
    )
    assert resp.status_code == 200
    assert "No hay vuelos disponibles" in resp.text


async def test_buscar_con_resultados_muestra_vuelo(client, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory(origen_codigo="JFK", destino_codigo="LAX", fecha_salida="2027-06-15")
    await tarifa_factory(vuelo["id"], cupos_disponibles=10, precio_final=250.0)

    resp = await client.get(
        "/vuelos/buscar",
        params={"origen": "JFK", "destino": "LAX", "fecha": "2027-06-15", "pasajeros": 1},
    )
    assert resp.status_code == 200
    assert vuelo["numero_vuelo"] in resp.text
    assert "$250" in resp.text  # precio_desde se muestra sin decimales ("%.0f") en el layout de resultados


async def test_filtros_secundarios_sin_boton_aplicar(client, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory(origen_codigo="JFK", destino_codigo="LAX", fecha_salida="2027-06-16")
    await tarifa_factory(vuelo["id"])

    resp = await client.get(
        "/vuelos/buscar",
        params={"origen": "JFK", "destino": "LAX", "fecha": "2027-06-16", "pasajeros": 1},
    )
    html = resp.text
    # Sort tabs y filtro de aerolínea envían el form oculto (#form-filtros) al
    # interactuar (filterByAirline/sortBy -> .submit()), sin botón "Aplicar".
    assert "filterByAirline" in html
    assert ">Aplicar<" not in html
    # La búsqueda principal sí conserva su botón explícito (icono de lupa).
    assert 'id="form-busqueda"' in html


# ── CU-O18 / RF-VUE-002 (CHK003, RNF-VUE-001/CHK015) ─────────────────────

async def test_detalle_muestra_tres_niveles_con_precio_y_politica(client, pb, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory(origen_codigo="JFK", destino_codigo="LAX")
    niveles = (await pb.list_records("niveles_tarifa", {"perPage": 10}))["items"]
    assert len(niveles) == 3
    for i, nivel in enumerate(niveles):
        await tarifa_factory(vuelo["id"], precio_final=100.0 + i * 10, nivel_tarifa_id=nivel["id"])

    resp = await client.get(f"/vuelos/{vuelo['id']}")
    assert resp.status_code == 200
    html = resp.text
    for nivel in niveles:
        assert nivel["nombre"] in html

    politica_ids = {n["politica_reembolso_id"] for n in niveles}
    for politica_id in politica_ids:
        politica = await pb.get_record("politicas_reembolso", politica_id)
        assert politica["nombre"] in html


async def test_origen_destino_legibles_no_solo_codigo_iata(client, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory(origen_codigo="JFK", destino_codigo="LAX")
    await tarifa_factory(vuelo["id"])

    esperado_origen = await resolver_aeropuerto("JFK")
    esperado_destino = await resolver_aeropuerto("LAX")
    assert esperado_origen != "JFK"  # confirma que la resolución realmente agrega nombre de ciudad

    resp = await client.get(f"/vuelos/{vuelo['id']}")
    assert esperado_origen in resp.text
    assert esperado_destino in resp.text


async def test_detalle_vuelo_inexistente_da_404(client):
    resp = await client.get("/vuelos/id-que-no-existe")
    assert resp.status_code == 404
