async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    return resp


# ── RF-SEG-006 (CHK009) ───────────────────────────────────────────────────

async def test_ver_perfil_muestra_datos_propios(client, usuario_factory):
    usuario = await usuario_factory()
    await _login(client, usuario)
    resp = await client.get("/mi-perfil")
    assert resp.status_code == 200
    assert usuario["email"] in resp.text
    assert usuario["nombre_completo"] in resp.text


async def test_editar_perfil_actualiza_nombre(client, usuario_factory, pb):
    usuario = await usuario_factory()
    await _login(client, usuario)
    resp = await client.post("/mi-perfil", data={"nombre_completo": "Nombre Editado"})
    assert resp.status_code == 200
    assert "Nombre Editado" in resp.text

    actualizado = await pb.get_record("usuarios", usuario["id"])
    assert actualizado["nombre_completo"] == "Nombre Editado"


# ── RF-SEG-007 (CHK010, RN-SEG-005/CHK027) ────────────────────────────────

async def test_cambiar_password_exige_actual_correcta(client, usuario_factory):
    usuario = await usuario_factory()
    await _login(client, usuario)
    resp = await client.post(
        "/mi-perfil/cambiar-password",
        data={
            "password_actual": "clave-incorrecta",
            "password_nueva": "NuevaClave#456",
            "confirmacion": "NuevaClave#456",
        },
    )
    assert resp.status_code == 400
    assert "no es correcta" in resp.text


async def test_cambiar_password_rechaza_politica_debil(client, usuario_factory):
    usuario = await usuario_factory()
    await _login(client, usuario)
    resp = await client.post(
        "/mi-perfil/cambiar-password",
        data={
            "password_actual": usuario["_password"],
            "password_nueva": "abc",
            "confirmacion": "abc",
        },
    )
    assert resp.status_code == 400


async def test_cambiar_password_exitoso_permite_login_con_nueva(client, usuario_factory):
    usuario = await usuario_factory()
    await _login(client, usuario)
    resp = await client.post(
        "/mi-perfil/cambiar-password",
        data={
            "password_actual": usuario["_password"],
            "password_nueva": "NuevaClave#456",
            "confirmacion": "NuevaClave#456",
        },
    )
    assert resp.status_code == 200
    assert "actualizada" in resp.text

    await client.post("/logout")
    login_resp = await client.post(
        "/login", data={"email": usuario["email"], "password": "NuevaClave#456"}
    )
    assert login_resp.status_code == 303


# ── RF-SEG-017 (CHK022, RN-SEG-011/CHK033) ────────────────────────────────

async def test_solicitar_eliminacion_registra_solicitud(client, usuario_factory, pb):
    usuario = await usuario_factory()
    await _login(client, usuario)
    resp = await client.post("/mi-perfil/solicitar-eliminacion")
    assert resp.status_code == 200
    assert "eliminación" in resp.text.lower()

    registro = await pb.get_first(
        "auditoria", f'accion="solicitud_eliminacion_datos" && registro_id="{usuario["id"]}"'
    )
    assert registro is not None
    await pb.delete_record("auditoria", registro["id"])
