"""RF-CTA-003/RN-CTA-001 — cada módulo de producto escribe su propia
búsqueda (`registrar_busqueda_reciente`); Cuenta solo lee y relanza."""


async def _login(client, usuario):
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303


async def test_buscar_vuelos_logueado_registra_busqueda_reciente(client, pb, pasajero_factory, vuelo_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    await _login(client, usuario)

    resp = await client.get(
        "/vuelos/buscar", params={"origen": "JFK", "destino": "LAX", "fecha": "2027-01-01", "pasajeros": 1}
    )
    assert resp.status_code == 200

    busquedas = await pb.list_records(
        "busquedas_recientes", {"filter": f'pasajero_id="{pasajero["id"]}" && tipo_producto="vuelo"'}
    )
    assert busquedas["totalItems"] == 1
    assert busquedas["items"][0]["criterios"]["destino"] == "LAX"

    for b in busquedas["items"]:
        await pb.delete_record("busquedas_recientes", b["id"])


async def test_buscar_anonimo_no_registra_busqueda(client, pb, vuelo_factory):
    await vuelo_factory()
    antes = (await pb.list_records("busquedas_recientes", {"perPage": 1}))["totalItems"]

    resp = await client.get(
        "/vuelos/buscar", params={"origen": "JFK", "destino": "LAX", "fecha": "2027-01-01"}
    )
    assert resp.status_code == 200

    despues = (await pb.list_records("busquedas_recientes", {"perPage": 1}))["totalItems"]
    assert despues == antes


async def test_listar_y_relanzar_busqueda_reciente(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    busqueda = await pb.create_record(
        "busquedas_recientes",
        {
            "pasajero_id": pasajero["id"], "tipo_producto": "hotel",
            "criterios": {"ciudad": "Miami", "checkin": "", "checkout": "", "huespedes": 2},
            "fecha": "2027-01-01 00:00:00.000Z",
        },
    )

    await _login(client, usuario)
    resp = await client.get("/mis-busquedas-recientes")
    assert resp.status_code == 200
    assert "Miami" in resp.text

    resp = await client.post(f"/mis-busquedas-recientes/{busqueda['id']}/relanzar")
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/hoteles/buscar?")
    assert "Miami" in resp.headers["location"]

    await pb.delete_record("busquedas_recientes", busqueda["id"])
