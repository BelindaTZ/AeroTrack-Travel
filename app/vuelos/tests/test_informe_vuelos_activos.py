"""IS-11 (auditoría de informes simples, sesión 2026-08-01) — filtros de
aerolínea/ruta/nivel de riesgo, paginación y exportar CSV sobre el
dashboard de vuelos activos (CU-T19), ya existente. El nivel de riesgo se
calcula en vivo a partir del histórico OTP real (parquet
`agg_otp_aerolinea_mes`), no hay datos de riesgo sembrados por prueba —
por eso estos tests usan aerolíneas reales cuyo riesgo actual se consulta
antes de armar la aserción, en vez de asumir un valor fijo."""

from app.disrupciones.services.riesgo_service import riesgo_estimado_por_aerolinea


async def _aerolinea_por_iata(pb, iata: str) -> dict:
    return await pb.get_first("aerolineas", f'codigo_iata="{iata}"')


async def test_filtro_por_aerolinea(admin_client, pb, vuelo_factory):
    # rutas ficticias únicas — evita que la paginación (25/página, orden por
    # fecha de salida) empuje este vuelo de prueba fuera de la página 1
    # entre el volumen real de vuelos "programado" ya sembrados en la BD
    # compartida.
    aerolinea = await _aerolinea_por_iata(pb, "DL")
    vuelo = await vuelo_factory(
        estado="programado", aerolinea_id=aerolinea["id"], origen_codigo="XA1", destino_codigo="XA2"
    )

    resp = await admin_client.get(f"/backoffice/vuelos/activos?aerolinea_id={aerolinea['id']}&ruta=XA1")
    assert resp.status_code == 200
    assert vuelo["numero_vuelo"] in resp.text


async def test_filtro_por_ruta(admin_client, vuelo_factory):
    vuelo = await vuelo_factory(estado="programado", origen_codigo="ZZZ", destino_codigo="YYY")

    resp = await admin_client.get("/backoffice/vuelos/activos?ruta=ZZZ")
    assert resp.status_code == 200
    assert vuelo["numero_vuelo"] in resp.text

    resp_otro = await admin_client.get("/backoffice/vuelos/activos?ruta=QQQ")
    assert vuelo["numero_vuelo"] not in resp_otro.text


async def test_filtro_por_nivel_de_riesgo(admin_client, pb, vuelo_factory):
    riesgo = await riesgo_estimado_por_aerolinea()
    iata_alto = next((k for k, v in riesgo.items() if v >= 20), None)
    assert iata_alto is not None, "se esperaba al menos una aerolínea con riesgo alto en el parquet real"
    aerolinea = await _aerolinea_por_iata(pb, iata_alto)
    if aerolinea is None:
        import pytest
        pytest.skip(f"aerolínea {iata_alto} no está sembrada en `aerolineas`")

    vuelo = await vuelo_factory(
        estado="programado", aerolinea_id=aerolinea["id"], origen_codigo="XB1", destino_codigo="XB2"
    )

    resp = await admin_client.get("/backoffice/vuelos/activos?nivel_riesgo=alto&ruta=XB1")
    assert resp.status_code == 200
    assert vuelo["numero_vuelo"] in resp.text

    resp_bajo = await admin_client.get("/backoffice/vuelos/activos?nivel_riesgo=bajo&ruta=XB1")
    assert vuelo["numero_vuelo"] not in resp_bajo.text


async def test_paginacion(admin_client):
    resp = await admin_client.get("/backoffice/vuelos/activos?page=1")
    assert resp.status_code == 200

    resp = await admin_client.get("/backoffice/vuelos/activos?page=999")
    assert resp.status_code == 200


async def test_exportar_csv(admin_client, vuelo_factory):
    vuelo = await vuelo_factory(estado="programado", origen_codigo="ZZZ", destino_codigo="YYY")

    resp = await admin_client.get("/backoffice/vuelos/activos/exportar?ruta=ZZZ")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert resp.text.splitlines()[0] == (
        "numero_vuelo,aerolinea,origen,destino,fecha_salida,hora_salida_programada,estado,riesgo_pct,nivel_riesgo"
    )
    assert vuelo["numero_vuelo"] in resp.text
