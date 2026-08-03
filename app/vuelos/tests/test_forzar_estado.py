"""RF-VUE-006 (CU-O48) — camino EXCEPCIONAL. Ninguna prueba de CU-O19/O20
(test_catalogo_service.py, test_estado_service.py) importa nada de este
módulo — el flujo automático normal no depende de que CU-O48 exista."""


# ── CHK007 parte 1: sin sesión ────────────────────────────────────────────

async def test_forzar_estado_sin_sesion_bloqueado(client, vuelo_factory):
    vuelo = await vuelo_factory()
    resp = await client.post(
        f"/backoffice/vuelos/{vuelo['id']}/forzar-estado",
        data={"nuevo_estado": "retrasado", "motivo": "demo"},
    )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/login")


# ── CHK007 parte 2: sin permiso RBAC ──────────────────────────────────────

async def test_forzar_estado_sin_permiso_rbac_bloqueado(client, usuario_factory, vuelo_factory):
    vuelo = await vuelo_factory()
    # el rol "Pasajero" no tiene permiso Nivel 1 sobre vuelos_catalogo -> RBAC bloquea
    pasajero = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})

    resp = await client.post(
        f"/backoffice/vuelos/{vuelo['id']}/forzar-estado",
        data={"nuevo_estado": "retrasado", "motivo": "demo"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 403


# ── CHK007 parte 3 / CHK014: sin motivo ───────────────────────────────────

async def test_forzar_estado_sin_motivo_rechazado(admin_client, pb, vuelo_factory):
    vuelo = await vuelo_factory(estado="programado")

    resp = await admin_client.post(
        f"/backoffice/vuelos/{vuelo['id']}/forzar-estado",
        data={"nuevo_estado": "retrasado", "motivo": "   "},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 400
    assert "motivo" in resp.json()["detail"].lower()

    sin_cambios = await pb.get_record("vuelos_catalogo", vuelo["id"])
    assert sin_cambios["estado"] == "programado"


# ── CHK008, CHK013: camino feliz ──────────────────────────────────────────

async def test_forzar_estado_exitoso_marca_manual_y_audita(admin_client, pb, vuelo_factory):
    vuelo = await vuelo_factory(estado="programado", generado_por="sistema")

    resp = await admin_client.post(
        f"/backoffice/vuelos/{vuelo['id']}/forzar-estado",
        data={"nuevo_estado": "retrasado", "motivo": "demo sustentación"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200

    actualizado = await pb.get_record("vuelos_catalogo", vuelo["id"])
    assert actualizado["estado"] == "retrasado"
    assert actualizado["generado_por"] == "manual"  # RN-VUE-005: distinguible de un cambio real

    registro = await pb.get_first(
        "auditoria", f'accion="forzar_estado" && registro_id="{vuelo["id"]}"'
    )
    assert registro is not None
    assert registro["detalle"]["motivo"] == "demo sustentación"
    assert registro["detalle"]["notificacion"] == "pendiente_de_modulo_disrupciones"
    await pb.delete_record("auditoria", registro["id"])
