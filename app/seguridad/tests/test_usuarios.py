import uuid


# ── RF-SEG-009 (CHK013) ───────────────────────────────────────────────────

async def test_crear_usuario_interno_con_rol_obligatorio(admin_client, pb, rol_agente):
    email = f"interno.{uuid.uuid4().hex[:10]}@aerotrack.test"
    resp = await admin_client.post(
        "/admin/usuarios",
        data={
            "nombre_completo": "Agente de Prueba",
            "email": email,
            "password": "ClaveSegura#123",
            "rol_id": rol_agente["id"],
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Usuario creado" in resp.text

    creado = await pb.get_first("usuarios", f'email="{email}"')
    assert creado is not None
    assert creado["rol_id"] == rol_agente["id"]

    await pb.delete_record("usuarios", creado["id"])


async def test_editar_usuario_interno_cambia_rol_y_desactiva(
    admin_client, pb, rol_agente, rol_administrador, usuario_factory
):
    usuario = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])

    resp = await admin_client.put(
        f"/admin/usuarios/{usuario['id']}",
        data={"rol_id": rol_administrador["id"], "activo": "false"},
    )
    assert resp.status_code == 200

    actualizado = await pb.get_record("usuarios", usuario["id"])
    assert actualizado["rol_id"] == rol_administrador["id"]
    assert actualizado["activo"] is False


async def test_usuario_desactivado_no_puede_iniciar_sesion(admin_client, client, usuario_factory, rol_agente):
    usuario = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])
    await admin_client.put(f"/admin/usuarios/{usuario['id']}", data={"activo": "false"})

    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 403


async def test_editar_usuario_interno_cambia_nombre(admin_client, pb, rol_agente, usuario_factory):
    usuario = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])

    resp = await admin_client.put(
        f"/admin/usuarios/{usuario['id']}",
        data={"nombre_completo": "Nombre Editado Por Admin"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["nombre_completo"] == "Nombre Editado Por Admin"

    actualizado = await pb.get_record("usuarios", usuario["id"])
    assert actualizado["nombre_completo"] == "Nombre Editado Por Admin"


# ── Reseteo de contraseña iniciado por Administrador ─────────────────────

async def test_admin_resetea_password_genera_token_y_audita(admin_client, pb, rol_agente, usuario_factory):
    usuario = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])

    resp = await admin_client.post(
        f"/admin/usuarios/{usuario['id']}/resetear-password",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200

    actualizado = await pb.get_record("usuarios", usuario["id"])
    assert actualizado["reset_token_hash"]
    assert actualizado["reset_token_expira"]

    registro = await pb.get_first(
        "auditoria", f'accion="resetear_password" && registro_id="{usuario["id"]}"'
    )
    assert registro is not None
    assert registro["detalle"]["iniciado_por_admin"] is True
    await pb.delete_record("auditoria", registro["id"])


# ── WP-02 (auditoría de WorkPanels, 2026-07-31) — filtros ────────────────

async def test_filtros_usuarios_backoffice(admin_client, rol_agente, usuario_factory):
    usuario = await usuario_factory(
        tipo_actor="agente", rol_id=rol_agente["id"], nombre_completo="Zoraida Filtro Usuario"
    )

    resp = await admin_client.get("/admin/usuarios", params={"nombre": "Zoraida Filtro"})
    assert resp.status_code == 200
    assert "Zoraida Filtro Usuario" in resp.text

    resp = await admin_client.get("/admin/usuarios", params={"rol_id": rol_agente["id"]})
    assert resp.status_code == 200
    assert "Zoraida Filtro Usuario" in resp.text

    resp = await admin_client.get("/admin/usuarios", params={"estado": "inactivo"})
    assert resp.status_code == 200
    assert "Zoraida Filtro Usuario" not in resp.text  # está activo, no debe aparecer en "inactivo"
