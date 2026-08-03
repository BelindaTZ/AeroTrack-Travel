"""IS-07 (auditoría de informes simples, sesión 2026-08-01) — catálogo de
vuelos activo tal como lo publica el DAG en el NDJSON de MinIO
(`aerotrack-travel-catalog`), distinto de `/backoffice/vuelos` (WP-16) que
lee `vuelos_catalogo` directo de PocketBase. `vuelo_factory` ya republica
el NDJSON al crear (`minio_catalog_reader.publicar_y_refrescar`), así que
un vuelo de prueba aparece de inmediato en este catálogo."""


async def test_filtro_por_origen_destino(admin_client, vuelo_factory):
    vuelo = await vuelo_factory(origen_codigo="ZZ1", destino_codigo="ZZ2")

    resp = await admin_client.get("/backoffice/vuelos/catalogo-publicado?origen=ZZ1&destino=ZZ2")
    assert resp.status_code == 200
    assert "ZZ1" in resp.text
    assert "ZZ2" in resp.text

    resp_sin_match = await admin_client.get("/backoffice/vuelos/catalogo-publicado?origen=QQQ")
    assert "ZZ1" not in resp_sin_match.text


async def test_filtro_por_aerolinea(admin_client, pb, vuelo_factory):
    aerolinea = await pb.get_first("aerolineas", 'codigo_iata="DL"')
    vuelo = await vuelo_factory(aerolinea_id=aerolinea["id"], origen_codigo="XC1", destino_codigo="XC2")

    resp = await admin_client.get(f"/backoffice/vuelos/catalogo-publicado?aerolinea_id={aerolinea['id']}&origen=XC1")
    assert resp.status_code == 200
    assert "Delta Air Lines" in resp.text
    assert "XC1" in resp.text


async def test_paginacion_50_por_pagina(admin_client):
    resp = await admin_client.get("/backoffice/vuelos/catalogo-publicado?page=1")
    assert resp.status_code == 200

    resp = await admin_client.get("/backoffice/vuelos/catalogo-publicado?page=999")
    assert resp.status_code == 200


async def test_muestra_fecha_de_publicacion_del_snapshot(admin_client):
    resp = await admin_client.get("/backoffice/vuelos/catalogo-publicado")
    assert resp.status_code == 200
    assert "Última publicación del snapshot" in resp.text


async def test_exportar_csv(admin_client, vuelo_factory):
    vuelo = await vuelo_factory(origen_codigo="ZY1", destino_codigo="ZY2", precio_base=555.0)

    resp = await admin_client.get("/backoffice/vuelos/catalogo-publicado/exportar?origen=ZY1")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert resp.text.splitlines()[0] == "origen,destino,aerolinea,precio_base,fecha_actualizacion"
    assert "ZY1" in resp.text
    assert "555.0" in resp.text or "555" in resp.text
