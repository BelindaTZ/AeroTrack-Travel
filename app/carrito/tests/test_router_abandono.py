"""CU-T26/T27 — RBAC y flujo de los endpoints de backoffice."""

from app.carrito.services.abandono_service import DEFAULT_ASUNTO, DEFAULT_CUERPO, DEFAULT_UMBRAL_HORAS


async def test_config_abandono_requiere_permiso_admin(client, usuario_factory):
    pasajero = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})
    resp = await client.get("/backoffice/carrito/config-abandono")
    assert resp.status_code == 403


async def test_config_abandono_admin_ve_formulario_con_defaults(admin_client):
    resp = await admin_client.get("/backoffice/carrito/config-abandono")
    assert resp.status_code == 200
    assert "umbral_horas" in resp.text


async def test_config_abandono_admin_actualiza_valores(admin_client):
    # Config real, no aislada por fixture — se restaura al default después
    # de la prueba para no dejar la pantalla de administración con datos de
    # prueba visibles en el ambiente compartido.
    try:
        resp = await admin_client.post(
            "/backoffice/carrito/config-abandono",
            data={
                "umbral_horas": "3.5",
                "plantilla_asunto": "Prueba de asunto",
                "plantilla_cuerpo": "Prueba de cuerpo",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        verificacion = await admin_client.get("/backoffice/carrito/config-abandono")
        assert "3.5" in verificacion.text
        assert "Prueba de asunto" in verificacion.text
    finally:
        await admin_client.post(
            "/backoffice/carrito/config-abandono",
            data={
                "umbral_horas": DEFAULT_UMBRAL_HORAS,
                "plantilla_asunto": DEFAULT_ASUNTO,
                "plantilla_cuerpo": DEFAULT_CUERPO,
            },
        )


async def test_config_abandono_rechaza_umbral_no_positivo(admin_client):
    resp = await admin_client.post(
        "/backoffice/carrito/config-abandono",
        data={"umbral_horas": "0", "plantilla_asunto": "x", "plantilla_cuerpo": "y"},
    )
    assert resp.status_code == 400


async def test_reporte_requiere_permiso_admin(client, usuario_factory):
    pasajero = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})
    resp = await client.get("/backoffice/carrito/reporte")
    assert resp.status_code == 403


async def test_reporte_admin_ve_totales(admin_client):
    resp = await admin_client.get("/backoffice/carrito/reporte?dias=7")
    assert resp.status_code == 200
    assert "Tasa de recuperaci" in resp.text
