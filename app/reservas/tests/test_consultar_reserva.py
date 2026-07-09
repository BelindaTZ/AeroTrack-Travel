async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


# ── RF-RES-005 (CHK007, CHK022) ────────────────────────────────────────────

async def test_ver_reserva_ajena_bloqueada(client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, _pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero_a["id"], vuelo["id"], tarifa["id"])

    await _login(client, usuario_b)
    resp = await client.get(f"/reservas/{reserva['id']}")
    assert resp.status_code == 404  # ni existencia se revela a quien no es dueño


async def test_ver_reserva_propia_permitida(client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])

    await _login(client, usuario)
    resp = await client.get(f"/reservas/{reserva['id']}")
    assert resp.status_code == 200
    assert reserva["codigo_reserva"] in resp.text


async def test_mis_reservas_solo_muestra_las_propias(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva_a = await reserva_factory(pasajero_a["id"], vuelo["id"], tarifa["id"])
    reserva_b = await reserva_factory(pasajero_b["id"], vuelo["id"], tarifa["id"])

    await _login(client, usuario_a)
    resp = await client.get("/reservas")
    assert resp.status_code == 200
    assert reserva_a["codigo_reserva"] in resp.text
    assert reserva_b["codigo_reserva"] not in resp.text
