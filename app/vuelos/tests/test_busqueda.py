from app.shared import minio_catalog_reader
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


# ── RF-VUE-007 (filtros reales: horario multi-select, equipaje) ──────────

async def test_filtro_horario_multiselect_filtra_por_franja(client, vuelo_factory, tarifa_factory):
    madrugada = await vuelo_factory(
        origen_codigo="JFK", destino_codigo="LAX", fecha_salida="2027-07-01",
        numero_vuelo="AA100", hora_salida_programada="03:00",
    )
    tarde = await vuelo_factory(
        origen_codigo="JFK", destino_codigo="LAX", fecha_salida="2027-07-01",
        numero_vuelo="AA200", hora_salida_programada="14:00",
    )
    await tarifa_factory(madrugada["id"])
    await tarifa_factory(tarde["id"])

    resp = await client.get(
        "/vuelos/buscar",
        params={"origen": "JFK", "destino": "LAX", "fecha": "2027-07-01", "horario": "tarde"},
    )
    assert resp.status_code == 200
    assert "AA200" in resp.text
    assert "AA100" not in resp.text


async def test_filtro_horario_sin_seleccion_muestra_todo(client, vuelo_factory, tarifa_factory):
    """Ninguna franja marcada = sin filtro (mismo criterio que aerolíneas),
    no "cero resultados" — RF-VUE-007."""
    madrugada = await vuelo_factory(
        origen_codigo="JFK", destino_codigo="LAX", fecha_salida="2027-07-02",
        numero_vuelo="AA300", hora_salida_programada="03:00",
    )
    await tarifa_factory(madrugada["id"])

    resp = await client.get(
        "/vuelos/buscar", params={"origen": "JFK", "destino": "LAX", "fecha": "2027-07-02"}
    )
    assert "AA300" in resp.text


async def test_filtro_equipaje_incluido_excluye_vuelos_solo_light(client, pb, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory(origen_codigo="JFK", destino_codigo="LAX", fecha_salida="2027-07-03", numero_vuelo="AA400")
    nivel_light = await pb.get_first("niveles_tarifa", 'nombre="Light"')
    await tarifa_factory(vuelo["id"], nivel_tarifa_id=nivel_light["id"])  # única tarifa, sin equipaje incluido

    resp_filtrado = await client.get(
        "/vuelos/buscar",
        params={"origen": "JFK", "destino": "LAX", "fecha": "2027-07-03", "equipaje": "true"},
    )
    assert "AA400" not in resp_filtrado.text

    resp_sin_filtro = await client.get(
        "/vuelos/buscar", params={"origen": "JFK", "destino": "LAX", "fecha": "2027-07-03"}
    )
    assert "AA400" in resp_sin_filtro.text  # sin el filtro, el mismo vuelo sí aparece


async def test_sidebar_no_ofrece_filtro_de_escalas_no_implementable(client, vuelo_factory, tarifa_factory):
    """El modelo no tiene concepto de escalas (todo vuelo es un tramo único,
    ver google_flights_client.py) — un filtro decorativo que no filtra nada
    es peor que no tenerlo, se sacó de la sidebar."""
    vuelo = await vuelo_factory(origen_codigo="JFK", destino_codigo="LAX", fecha_salida="2027-07-04")
    await tarifa_factory(vuelo["id"])

    resp = await client.get(
        "/vuelos/buscar", params={"origen": "JFK", "destino": "LAX", "fecha": "2027-07-04"}
    )
    assert "Escalas" not in resp.text


# ── RF-VUE-008 / CU-O51 (mostrar predicción de precio) ────────────────────

async def test_prediccion_de_precio_se_muestra_cuando_existe(client, pb, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory(origen_codigo="JFK", destino_codigo="LAX", fecha_salida="2027-07-05")
    await tarifa_factory(vuelo["id"])
    prediccion = await pb.create_record(
        "predicciones_precio_ruta",
        {
            "origen_codigo": "JFK", "destino_codigo": "LAX", "fecha_objetivo": "2027-07-05",
            "precio_minimo_historico": 94.0, "nivel_precio": "typical",
            "rango_tipico_min": 75.0, "rango_tipico_max": 155.0, "historico_precios": [],
            "precio_predicho": 115.0, "tendencia": "bajando", "confianza": 0.6,
            "fecha_calculo": "2027-07-01 00:00:00.000Z",
        },
    )
    # STAGING (ver plan de migración): la búsqueda lee el snapshot NDJSON en
    # MinIO, no PocketBase directo — republicar para que sea visible ya.
    await minio_catalog_reader.publicar_y_refrescar("predicciones_precio_ruta")

    try:
        resp = await client.get(
            "/vuelos/buscar", params={"origen": "JFK", "destino": "LAX", "fecha": "2027-07-05"}
        )
        assert "Precio bajando" in resp.text
        assert "$75" in resp.text and "$155" in resp.text
    finally:
        await pb.delete_record("predicciones_precio_ruta", prediccion["id"])
        await minio_catalog_reader.publicar_y_refrescar("predicciones_precio_ruta")


async def test_sin_prediccion_no_muestra_banner(client, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory(origen_codigo="JFK", destino_codigo="LAX", fecha_salida="2027-07-06")
    await tarifa_factory(vuelo["id"])

    resp = await client.get(
        "/vuelos/buscar", params={"origen": "JFK", "destino": "LAX", "fecha": "2027-07-06"}
    )
    assert "Precio bajando" not in resp.text
    assert "Precio estable" not in resp.text
    assert "Precio subiendo" not in resp.text
