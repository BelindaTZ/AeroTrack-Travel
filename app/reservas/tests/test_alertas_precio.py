async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


# ── RF-RES-006 (CHK008, CHK023) ────────────────────────────────────────────

async def test_crear_alerta_de_precio_queda_activa(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    await _login(client, usuario)

    resp = await client.post(
        "/alertas-precio",
        data={
            "origen": "jfk",
            "destino": "lax",
            "fecha_objetivo": "2027-08-01",
            "precio_umbral": "150.0",
        },
    )
    assert resp.status_code == 303

    alerta = await pb.get_first(
        "alertas_precio", f'pasajero_id="{pasajero["id"]}" && origen_codigo="JFK"'
    )
    assert alerta is not None
    assert alerta["activa"] is True
    assert alerta["destino_codigo"] == "LAX"
    assert alerta["precio_umbral"] == 150.0

    await pb.delete_record("alertas_precio", alerta["id"])
