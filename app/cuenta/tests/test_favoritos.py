"""RF-CTA-002 — guardar/eliminar favorito de tipo destino/hotel/actividad."""


async def _login(client, usuario):
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303


async def test_guardar_y_listar_favorito(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    await _login(client, usuario)

    resp = await client.post(
        "/favoritos", data={"tipo": "destino", "producto_ref": "JFK — Nueva York"}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert "JFK" in resp.text

    favoritos = await pb.list_records("favoritos", {"filter": f'pasajero_id="{pasajero["id"]}"'})
    assert favoritos["totalItems"] == 1
    for f in favoritos["items"]:
        await pb.delete_record("favoritos", f["id"])


async def test_tipo_invalido_no_crea_favorito(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    await _login(client, usuario)

    resp = await client.post(
        "/favoritos", data={"tipo": "no_valido", "producto_ref": "x"}, follow_redirects=True
    )
    assert resp.status_code == 200

    favoritos = await pb.list_records("favoritos", {"filter": f'pasajero_id="{pasajero["id"]}"'})
    assert favoritos["totalItems"] == 0


async def test_eliminar_favorito_ajeno_no_lo_borra(client, pb, pasajero_factory):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()

    favorito = await pb.create_record(
        "favoritos",
        {
            "pasajero_id": pasajero_a["id"], "tipo": "hotel", "producto_ref": "hotel-x",
            "fecha_guardado": "2027-01-01 00:00:00.000Z",
        },
    )

    await _login(client, usuario_b)
    resp = await client.post(f"/favoritos/{favorito['id']}/eliminar", follow_redirects=True)
    assert resp.status_code == 200

    sigue = await pb.get_record("favoritos", favorito["id"])
    assert sigue is not None
    await pb.delete_record("favoritos", favorito["id"])


async def test_eliminar_favorito_propio(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    favorito = await pb.create_record(
        "favoritos",
        {
            "pasajero_id": pasajero["id"], "tipo": "actividad", "producto_ref": "act-x",
            "fecha_guardado": "2027-01-01 00:00:00.000Z",
        },
    )

    await _login(client, usuario)
    resp = await client.post(f"/favoritos/{favorito['id']}/eliminar", follow_redirects=True)
    assert resp.status_code == 200

    favoritos = await pb.list_records("favoritos", {"filter": f'pasajero_id="{pasajero["id"]}"'})
    assert favoritos["totalItems"] == 0
