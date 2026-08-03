"""WP-16 (auditoría de WorkPanels, 2026-08-01) — catálogo de vuelos con
filtros/paginación, ajuste puntual de tarifa (motivo + auditoría, mismo
patrón que forzar-estado) y CRUD de aerolíneas (antes inexistente)."""

from app.vuelos.repositories.vuelos_repo import VuelosRepository


async def test_listar_catalogo_filtra_por_aerolinea_y_estado(admin_client, vuelo_factory):
    vuelo = await vuelo_factory(estado="programado")

    resp = await admin_client.get("/backoffice/vuelos", params={"aerolinea_id": vuelo["aerolinea_id"]})
    assert resp.status_code == 200
    assert vuelo["numero_vuelo"] in resp.text

    resp = await admin_client.get("/backoffice/vuelos", params={"estado": "cancelado"})
    assert resp.status_code == 200
    assert vuelo["numero_vuelo"] not in resp.text

    resp = await admin_client.get("/backoffice/vuelos", params={"origen": vuelo["origen_codigo"]})
    assert resp.status_code == 200
    assert vuelo["numero_vuelo"] in resp.text


async def test_ver_detalle_muestra_tarifas(admin_client, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=321.0)

    resp = await admin_client.get("/backoffice/vuelos", params={"aerolinea_id": vuelo["aerolinea_id"]})
    assert resp.status_code == 200
    assert "321.00" in resp.text
    assert f"modal-ajustar-{tarifa['id']}" in resp.text


async def test_ajustar_tarifa_sin_motivo_rechazado(admin_client, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=100.0)

    resp = await admin_client.post(
        f"/backoffice/vuelos/tarifas/{tarifa['id']}/ajustar",
        data={"precio_final": "150.0", "motivo": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "obligatorio" in resp.text.lower()

    sin_cambios = await VuelosRepository().obtener_tarifa(tarifa["id"])
    assert sin_cambios["precio_final"] == 100.0


async def test_ajustar_tarifa_exitoso_audita(admin_client, pb, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=100.0, cupos_disponibles=5)

    resp = await admin_client.post(
        f"/backoffice/vuelos/tarifas/{tarifa['id']}/ajustar",
        data={"precio_final": "180.0", "cupos_disponibles": "2", "motivo": "corrección manual de prueba"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Tarifa ajustada" in resp.text

    actualizada = await VuelosRepository().obtener_tarifa(tarifa["id"])
    assert actualizada["precio_final"] == 180.0
    assert actualizada["cupos_disponibles"] == 2

    auditoria = await pb.list_records(
        "auditoria", {"filter": f'accion="ajustar_tarifa_manual" && registro_id="{tarifa["id"]}"', "perPage": 1}
    )
    assert auditoria["totalItems"] == 1


async def test_pasajero_no_tiene_acceso_al_catalogo(client, usuario_factory):
    pasajero = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})
    resp = await client.get("/backoffice/vuelos", headers={"Accept": "application/json"})
    assert resp.status_code == 403


# ── aerolíneas (CRUD antes inexistente) ───────────────────────────────────

async def test_crear_editar_y_alternar_aerolinea(admin_client, pb):
    resp = await admin_client.post(
        "/backoffice/vuelos/aerolineas",
        data={"nombre": "TestAir WP16", "codigo_iata": "tw1", "comision_pactada_pct": 7.5, "contacto": "ops@testair.test"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "TestAir WP16" in resp.text
    assert "Aerolínea creada" in resp.text

    aerolinea = await pb.get_first("aerolineas", 'nombre="TestAir WP16"')
    assert aerolinea is not None
    assert aerolinea["codigo_iata"] == "TW1"
    assert aerolinea["activa"] is True

    try:
        resp = await admin_client.post(
            f"/backoffice/vuelos/aerolineas/{aerolinea['id']}",
            data={"nombre": "TestAir WP16", "codigo_iata": "TW1", "comision_pactada_pct": 9.0, "contacto": "nuevo@testair.test"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Aerolínea actualizada" in resp.text
        actualizada = await pb.get_record("aerolineas", aerolinea["id"])
        assert actualizada["comision_pactada_pct"] == 9.0

        resp = await admin_client.post(
            f"/backoffice/vuelos/aerolineas/{aerolinea['id']}/alternar-activa", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "desactivada" in resp.text.lower()
        desactivada = await pb.get_record("aerolineas", aerolinea["id"])
        assert desactivada["activa"] is False

        resp = await admin_client.post(
            f"/backoffice/vuelos/aerolineas/{aerolinea['id']}/alternar-activa", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "reactivada" in resp.text.lower()
    finally:
        await pb.delete_record("aerolineas", aerolinea["id"])


async def test_filtros_aerolineas_backoffice(admin_client, pb):
    aerolinea = await pb.create_record(
        "aerolineas", {"nombre": "FiltroUnicoWP16", "codigo_iata": "FU1", "activa": True}
    )
    try:
        resp = await admin_client.get("/backoffice/vuelos/aerolineas", params={"nombre": "FiltroUnicoWP16"})
        assert resp.status_code == 200
        assert "FiltroUnicoWP16" in resp.text

        resp = await admin_client.get("/backoffice/vuelos/aerolineas", params={"estado": "inactivo"})
        assert resp.status_code == 200
        assert "FiltroUnicoWP16" not in resp.text
    finally:
        await pb.delete_record("aerolineas", aerolinea["id"])
