"""RF-ACT-001,002,003,007,009 (CU-O65,O66,O67,O68,O70) — buscar, detalle
con reseñas/horarios y filtrar."""


async def test_buscar_sin_resultados_muestra_mensaje_claro(client):
    resp = await client.get("/actividades/buscar", params={"ciudad": "CiudadInexistente9999"})
    assert resp.status_code == 200
    assert "No hay actividades disponibles" in resp.text


async def test_buscar_con_resultados_muestra_actividad(client, actividad_factory):
    await actividad_factory(ciudad="Madrid", nombre="Tour del Prado", precio_desde=30.0)

    resp = await client.get("/actividades/buscar", params={"ciudad": "Madrid"})
    assert resp.status_code == 200
    assert "Tour del Prado" in resp.text
    assert "$30" in resp.text


async def test_filtro_precio_maximo_excluye_ofertas_caras(client, actividad_factory):
    await actividad_factory(ciudad="Miami", nombre="Barata", precio_desde=20.0)
    await actividad_factory(ciudad="Miami", nombre="Cara", precio_desde=200.0)

    resp = await client.get("/actividades/buscar", params={"ciudad": "Miami", "precio_max": 50})
    assert "Barata" in resp.text
    assert "Cara" not in resp.text


async def test_filtro_calificacion_minima(client, actividad_factory):
    await actividad_factory(ciudad="Roma", nombre="TopRated", calificacion_promedio=4.8)
    await actividad_factory(ciudad="Roma", nombre="BajaNota", calificacion_promedio=3.0)

    resp = await client.get("/actividades/buscar", params={"ciudad": "Roma", "calificacion_min": 4.0})
    assert "TopRated" in resp.text
    assert "BajaNota" not in resp.text


async def test_detalle_muestra_descripcion_resenas_y_horarios(client, actividad_factory, horario_factory, resena_factory):
    actividad = await actividad_factory(ciudad="Paris", nombre="Crucero por el Sena")
    await horario_factory(actividad["id"], fecha="2027-06-15", hora="09:00")
    await resena_factory(actividad["id"], autor="Ana", comentario="Muy recomendado")

    resp = await client.get(f"/actividades/{actividad['id']}")
    assert resp.status_code == 200
    assert "Crucero por el Sena" in resp.text
    assert "Ana" in resp.text
    assert "Muy recomendado" in resp.text
    assert "09:00" in resp.text
    assert 'action="/carrito/agregar"' in resp.text


async def test_detalle_filtra_horarios_por_fecha(client, actividad_factory, horario_factory):
    actividad = await actividad_factory(ciudad="Paris", nombre="Tour Louvre")
    await horario_factory(actividad["id"], fecha="2027-06-15", hora="09:00")
    await horario_factory(actividad["id"], fecha="2027-06-16", hora="14:00")

    resp = await client.get(f"/actividades/{actividad['id']}", params={"fecha": "2027-06-15"})
    assert "09:00" in resp.text
    assert "14:00" not in resp.text


async def test_detalle_actividad_inexistente_da_404(client):
    resp = await client.get("/actividades/id-que-no-existe")
    assert resp.status_code == 404
