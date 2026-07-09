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
            "tipo_actor": "agente",
            "rol_id": rol_agente["id"],
        },
    )
    assert resp.status_code == 200
    assert "Usuario creado" in resp.text

    creado = await pb.get_first("usuarios", f'email="{email}"')
    assert creado is not None
    assert creado["tipo_actor"] == "agente"
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
