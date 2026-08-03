import uuid


def _nombre_rol_prueba() -> str:
    return f"RolPrueba-{uuid.uuid4().hex[:8]}"


async def _crear_rol(
    admin_client, nombre: str, descripcion: str = "rol de prueba", tipo_panel: str = "backoffice"
):
    resp = await admin_client.post(
        "/admin/roles",
        data={"nombre": nombre, "descripcion": descripcion, "tipo_panel": tipo_panel},
        follow_redirects=True,
    )
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


# ── WP-03 (auditoría de WorkPanels, 2026-07-31) — filtros ────────────────

async def test_filtros_roles_backoffice(admin_client, pb):
    nombre = _nombre_rol_prueba()
    await _crear_rol(admin_client, nombre, tipo_panel="autoservicio")
    rol = await pb.get_first("roles", f'nombre="{nombre}"')
    try:
        resp = await admin_client.get("/admin/roles", params={"nombre": nombre})
        assert resp.status_code == 200
        assert nombre in resp.text

        resp = await admin_client.get("/admin/roles", params={"tipo_panel": "autoservicio"})
        assert resp.status_code == 200
        assert nombre in resp.text

        resp = await admin_client.get("/admin/roles", params={"tipo_panel": "backoffice"})
        assert resp.status_code == 200
        assert nombre not in resp.text
    finally:
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
            "tabla_nivel2": [f"{modulo_seguridad['id']}::usuarios::ver"],
        },
    )
    assert resp.status_code == 200

    nivel1 = await pb.list_records("roles_permisos", {"filter": f'rol_id="{rol["id"]}"'})
    assert nivel1["totalItems"] == 1
    nivel2 = await pb.list_records("roles_permisos_tablas", {"filter": f'rol_id="{rol["id"]}"'})
    assert nivel2["totalItems"] == 1
    assert nivel2["items"][0]["tabla"] == "usuarios"
    assert nivel2["items"][0]["accion"] == "ver"

    await pb.delete_record("roles_permisos_tablas", nivel2["items"][0]["id"])
    await pb.delete_record("roles_permisos", nivel1["items"][0]["id"])
    await pb.delete_record("roles", rol["id"])


# ── hallazgo de sesión 2026-08-01 — nombre/descripción editables desde la
# UI de matriz de permisos (antes eran <input type="hidden"> con el valor
# actual, nunca modificables) ──────────────────────────────────────────

async def test_editar_nombre_y_descripcion_de_rol_personalizado(admin_client, pb):
    nombre = _nombre_rol_prueba()
    await _crear_rol(admin_client, nombre)
    rol = await pb.get_first("roles", f'nombre="{nombre}"')

    nuevo_nombre = _nombre_rol_prueba()
    resp = await admin_client.put(
        f"/admin/roles/{rol['id']}",
        data={"nombre": nuevo_nombre, "descripcion": "descripción actualizada"},
    )
    assert resp.status_code == 200

    actualizado = await pb.get_record("roles", rol["id"])
    assert actualizado["nombre"] == nuevo_nombre
    assert actualizado["descripcion"] == "descripción actualizada"

    await pb.delete_record("roles", rol["id"])


async def test_editar_nombre_de_rol_sistema_se_ignora(admin_client, pb, rol_administrador):
    """RN-SEG — el nombre de un rol de sistema (Administrador/Agente/
    Pasajero) se usa en lookups literales por string en todo el código;
    renombrarlo rompería auth/resolución de tipo de actor en silencio.
    La descripción no tiene ese riesgo y sí se actualiza.

    IMPORTANTE: el form real siempre manda el checkbox state completo de
    la matriz de permisos (`FormData` sobre TODO el form) — replicamos eso
    acá pasando los `permiso_id` actuales explícitos, porque omitirlos
    hace que el PUT interprete "sin permiso_id" como "vaciar todos los
    permisos del rol" (ver `_reemplazar_nivel1`). Un descuido acá borró en
    vivo los 46 permisos de Administrador durante el desarrollo de este
    test — quedó documentado para no repetirlo."""
    permisos_actuales = await pb.list_records(
        "roles_permisos", {"filter": f'rol_id="{rol_administrador["id"]}"', "perPage": 500}
    )
    permiso_ids = [rp["permiso_id"] for rp in permisos_actuales["items"]]

    resp = await admin_client.put(
        f"/admin/roles/{rol_administrador['id']}",
        data={"nombre": "Superadmin", "descripcion": "descripción de prueba", "permiso_id": permiso_ids},
    )
    assert resp.status_code == 200

    actualizado = await pb.get_record("roles", rol_administrador["id"])
    assert actualizado["nombre"] == "Administrador"
    assert actualizado["descripcion"] == "descripción de prueba"

    permisos_despues = await pb.list_records(
        "roles_permisos", {"filter": f'rol_id="{rol_administrador["id"]}"', "perPage": 500}
    )
    assert permisos_despues["totalItems"] == len(permiso_ids)

    # revertir la descripción para no afectar otros tests que dependan de ella
    await pb.update_record("roles", rol_administrador["id"], {"descripcion": rol_administrador.get("descripcion") or ""})


async def test_editar_rol_nivel2_sin_nivel1_rechazado(admin_client, pb):
    nombre = _nombre_rol_prueba()
    await _crear_rol(admin_client, nombre)
    rol = await pb.get_first("roles", f'nombre="{nombre}"')
    modulo_seguridad = await pb.get_first("modulos", 'clave="seguridad"')

    # Nivel 2 para "seguridad" sin ningún permiso_id (Nivel 1) de ese módulo.
    resp = await admin_client.put(
        f"/admin/roles/{rol['id']}",
        data={"tabla_nivel2": [f"{modulo_seguridad['id']}::usuarios::ver"]},
    )
    assert resp.status_code == 400
    assert "RN-SEG-009" in resp.text or "Nivel 1" in resp.text

    nivel2 = await pb.list_records("roles_permisos_tablas", {"filter": f'rol_id="{rol["id"]}"'})
    assert nivel2["totalItems"] == 0  # nada se guardó

    await pb.delete_record("roles", rol["id"])


async def test_editar_rol_nivel2_excede_accion_de_nivel1_rechazado(admin_client, pb):
    """RN-SEG-009 extendida a nivel de tabla (2026-07-30): Nivel 1 solo
    otorga "ver" sobre el módulo, pero Nivel 2 intenta restringir "editar"
    en una tabla — se rechaza aunque el módulo sí esté autorizado, porque
    la acción puntual no lo está."""
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
            "tabla_nivel2": [f"{modulo_seguridad['id']}::usuarios::editar"],
        },
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
    usuario = await usuario_factory(tipo_actor="agente", rol_id=rol["id"])

    resp = await admin_client.delete(f"/admin/roles/{rol['id']}")
    assert resp.status_code == 409
    assert "reasígnalos" in resp.text.lower() or "usuario" in resp.text.lower()

    # `usuarios.rol_id` es una relación obligatoria (migración 2026-07-27):
    # PocketBase ahora rechaza borrar `rol` mientras este usuario lo
    # referencie, así que hay que soltar la referencia primero.
    await pb.delete_record("usuarios", usuario["id"])
    await pb.delete_record("roles", rol["id"])


async def test_eliminar_rol_sin_uso_permitido(admin_client, pb):
    nombre = _nombre_rol_prueba()
    await _crear_rol(admin_client, nombre)
    rol = await pb.get_first("roles", f'nombre="{nombre}"')

    resp = await admin_client.delete(f"/admin/roles/{rol['id']}")
    assert resp.status_code == 200

    assert await pb.get_first("roles", f'nombre="{nombre}"') is None
