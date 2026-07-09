import uuid


def _nombre_rol_prueba() -> str:
    return f"RolPrueba-{uuid.uuid4().hex[:8]}"


async def _crear_rol(admin_client, nombre: str, descripcion: str = "rol de prueba"):
    resp = await admin_client.post("/admin/roles", data={"nombre": nombre, "descripcion": descripcion})
    assert resp.status_code == 200
    return resp


# ── RF-SEG-010 (CHK014) ───────────────────────────────────────────────────

async def test_crear_rol_queda_sin_permisos(admin_client, pb):
    nombre = _nombre_rol_prueba()
    await _crear_rol(admin_client, nombre)
    rol = await pb.get_first("roles", f'nombre="{nombre}"')
    assert rol is not None
    assert rol["es_sistema"] is False

    permisos = await pb.list_records("roles_permisos", {"filter": f'rol_id="{rol["id"]}"'})
    assert permisos["totalItems"] == 0

    await pb.delete_record("roles", rol["id"])


# ── RF-SEG-011 / RN-SEG-009 (CHK015, CHK031) ─────────────────────────────

async def test_editar_rol_nivel1_y_nivel2(admin_client, pb):
    nombre = _nombre_rol_prueba()
    await _crear_rol(admin_client, nombre)
    rol = await pb.get_first("roles", f'nombre="{nombre}"')

    modulo_seguridad = await pb.get_first("modulos", 'clave="seguridad"')
    permiso_ver = await pb.get_first(
        "permisos", f'modulo_id="{modulo_seguridad["id"]}" && accion="ver"'
    )

    resp = await admin_client.put(
        f"/admin/roles/{rol['id']}",
        data={
            "permiso_id": [permiso_ver["id"]],
            "tabla_nivel2": [f"{modulo_seguridad['id']}::usuarios"],
        },
    )
    assert resp.status_code == 200

    nivel1 = await pb.list_records("roles_permisos", {"filter": f'rol_id="{rol["id"]}"'})
    assert nivel1["totalItems"] == 1
    nivel2 = await pb.list_records("roles_permisos_tablas", {"filter": f'rol_id="{rol["id"]}"'})
    assert nivel2["totalItems"] == 1
    assert nivel2["items"][0]["tabla"] == "usuarios"

    await pb.delete_record("roles_permisos_tablas", nivel2["items"][0]["id"])
    await pb.delete_record("roles_permisos", nivel1["items"][0]["id"])
    await pb.delete_record("roles", rol["id"])


async def test_editar_rol_nivel2_sin_nivel1_rechazado(admin_client, pb):
    nombre = _nombre_rol_prueba()
    await _crear_rol(admin_client, nombre)
    rol = await pb.get_first("roles", f'nombre="{nombre}"')
    modulo_seguridad = await pb.get_first("modulos", 'clave="seguridad"')

    # Nivel 2 para "seguridad" sin ningún permiso_id (Nivel 1) de ese módulo.
    resp = await admin_client.put(
        f"/admin/roles/{rol['id']}",
        data={"tabla_nivel2": [f"{modulo_seguridad['id']}::usuarios"]},
    )
    assert resp.status_code == 400
    assert "RN-SEG-009" in resp.text or "Nivel 1" in resp.text

    nivel2 = await pb.list_records("roles_permisos_tablas", {"filter": f'rol_id="{rol["id"]}"'})
    assert nivel2["totalItems"] == 0  # nada se guardó

    await pb.delete_record("roles", rol["id"])


# ── RF-SEG-012 / RN-SEG-007 (CHK016, CHK029) ─────────────────────────────

async def test_eliminar_rol_protegido_bloqueado(admin_client, rol_administrador):
    resp = await admin_client.delete(f"/admin/roles/{rol_administrador['id']}")
    assert resp.status_code == 409
    assert "protegido" in resp.text.lower()


# ── RN-SEG-008 (CHK030) ───────────────────────────────────────────────────

async def test_eliminar_rol_con_usuarios_asignados_bloqueado(admin_client, pb, usuario_factory):
    nombre = _nombre_rol_prueba()
    await _crear_rol(admin_client, nombre)
    rol = await pb.get_first("roles", f'nombre="{nombre}"')
    await usuario_factory(tipo_actor="agente", rol_id=rol["id"])

    resp = await admin_client.delete(f"/admin/roles/{rol['id']}")
    assert resp.status_code == 409
    assert "reasígnalos" in resp.text.lower() or "usuario" in resp.text.lower()

    await pb.delete_record("roles", rol["id"])


async def test_eliminar_rol_sin_uso_permitido(admin_client, pb):
    nombre = _nombre_rol_prueba()
    await _crear_rol(admin_client, nombre)
    rol = await pb.get_first("roles", f'nombre="{nombre}"')

    resp = await admin_client.delete(f"/admin/roles/{rol['id']}")
    assert resp.status_code == 200

    assert await pb.get_first("roles", f'nombre="{nombre}"') is None
