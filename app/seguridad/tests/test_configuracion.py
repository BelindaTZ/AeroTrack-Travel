"""CU-T03 — configuración del sistema (WP-08, auditoría de WorkPanels
2026-07-31): modal de edición en vez de página completa."""


async def test_ver_configuracion_muestra_valores_actuales(admin_client):
    resp = await admin_client.get("/admin/configuracion")
    assert resp.status_code == 200
    assert "Editar configuración" in resp.text


async def test_editar_configuracion_exitosa(pb, admin_client):
    resp = await admin_client.post(
        "/admin/configuracion",
        data={"min_length": 8, "requiere_numero": "true", "duracion_sesion_dias": 14},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Configuración actualizada" in resp.text
    assert "8" in resp.text

    registro = await pb.get_first("configuracion_sistema", 'clave="password.min_length"')
    assert registro["valor"] == "8"

    # revertir a los defaults para no afectar otros tests
    await admin_client.post(
        "/admin/configuracion",
        data={"min_length": 6, "requiere_numero": "false", "duracion_sesion_dias": 7},
        follow_redirects=True,
    )


async def test_editar_configuracion_longitud_invalida_se_rechaza(admin_client):
    resp = await admin_client.post(
        "/admin/configuracion",
        data={"min_length": 3, "requiere_numero": "false", "duracion_sesion_dias": 7},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "no puede ser menor a 6" in resp.text


async def test_agente_no_tiene_acceso_a_configuracion(agente_client):
    resp = await agente_client.get("/admin/configuracion")
    assert resp.status_code == 403


# ── ampliación de sesión 2026-08-01 — plantillas / feature flags /
# parámetros de negocio, todos filas de `configuracion_sistema` ──────────

async def test_ver_configuracion_muestra_plantillas_flags_y_parametros(admin_client):
    resp = await admin_client.get("/admin/configuracion")
    assert resp.status_code == 200
    assert "Plantillas de notificación" in resp.text
    assert "password_recovery.plantilla_asunto" in resp.text
    assert "Feature flags" in resp.text
    assert "pagos.stripe_habilitado" in resp.text
    assert "Parámetros de negocio" in resp.text
    assert "reservas.precio_extra_equipaje" in resp.text


async def test_editar_plantilla_notificacion(pb, admin_client):
    plantilla = await pb.get_first("configuracion_sistema", 'clave="bienvenida.plantilla_cuerpo"')
    original = plantilla["valor"]
    try:
        resp = await admin_client.post(
            f"/admin/configuracion/plantillas/{plantilla['id']}",
            data={"valor": "Texto de bienvenida editado en test"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Plantilla actualizada" in resp.text

        actualizada = await pb.get_record("configuracion_sistema", plantilla["id"])
        assert actualizada["valor"] == "Texto de bienvenida editado en test"
    finally:
        await pb.update_record("configuracion_sistema", plantilla["id"], {"valor": original})


async def test_editar_parametro_negocio(pb, admin_client):
    parametro = await pb.get_first("configuracion_sistema", 'clave="reservas.precio_extra_equipaje"')
    original = parametro["valor"]
    try:
        resp = await admin_client.post(
            f"/admin/configuracion/parametros/{parametro['id']}",
            data={"valor": "50.0"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Parámetro actualizado" in resp.text

        actualizado = await pb.get_record("configuracion_sistema", parametro["id"])
        assert actualizado["valor"] == "50.0"
    finally:
        await pb.update_record("configuracion_sistema", parametro["id"], {"valor": original})


async def test_crear_y_alternar_feature_flag(pb, admin_client):
    clave = "test_wp08.flag_de_prueba"
    resp = await admin_client.post(
        "/admin/configuracion/flags",
        data={"clave": clave, "descripcion": "Flag de prueba", "valor": "true"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Feature flag creado" in resp.text

    flag = await pb.get_first("configuracion_sistema", f'clave="{clave}"')
    assert flag is not None
    assert flag["valor"] == "true"
    try:
        resp = await admin_client.post(f"/admin/configuracion/flags/{flag['id']}/alternar", follow_redirects=True)
        assert resp.status_code == 200
        assert "desactivado" in resp.text.lower()
        actualizado = await pb.get_record("configuracion_sistema", flag["id"])
        assert actualizado["valor"] == "false"

        resp = await admin_client.post(f"/admin/configuracion/flags/{flag['id']}/alternar", follow_redirects=True)
        assert resp.status_code == 200
        assert "activado" in resp.text.lower()
        actualizado = await pb.get_record("configuracion_sistema", flag["id"])
        assert actualizado["valor"] == "true"
    finally:
        await pb.delete_record("configuracion_sistema", flag["id"])


async def test_crear_feature_flag_clave_duplicada_se_rechaza(pb, admin_client):
    resp = await admin_client.post(
        "/admin/configuracion/flags",
        data={"clave": "pagos.stripe_habilitado", "descripcion": "duplicado", "valor": "true"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Ya existe un feature flag" in resp.text
