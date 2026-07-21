"""RF-CTA-004 — crear/eliminar viaje personalizado (planificación libre)."""


async def _login(client, usuario):
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303


async def test_crear_viaje_personalizado(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    await _login(client, usuario)

    resp = await client.post(
        "/viajes-personalizados", data={"nombre": "Luna de miel", "descripcion": "Presupuesto ideas"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Luna de miel" in resp.text

    viajes = await pb.list_records("viajes_personalizados", {"filter": f'pasajero_id="{pasajero["id"]}"'})
    assert viajes["totalItems"] == 1
    for v in viajes["items"]:
        await pb.delete_record("viajes_personalizados", v["id"])


async def test_eliminar_viaje_personalizado(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    viaje = await pb.create_record(
        "viajes_personalizados", {"pasajero_id": pasajero["id"], "nombre": "Viaje a borrar", "descripcion": ""}
    )

    await _login(client, usuario)
    resp = await client.post(f"/viajes-personalizados/{viaje['id']}/eliminar", follow_redirects=True)
    assert resp.status_code == 200

    viajes = await pb.list_records("viajes_personalizados", {"filter": f'pasajero_id="{pasajero["id"]}"'})
    assert viajes["totalItems"] == 0


async def test_no_ve_viajes_de_otro_pasajero(client, pb, pasajero_factory):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()
    viaje = await pb.create_record(
        "viajes_personalizados", {"pasajero_id": pasajero_a["id"], "nombre": "Privado de A", "descripcion": ""}
    )

    await _login(client, usuario_b)
    resp = await client.get("/viajes-personalizados")
    assert resp.status_code == 200
    assert "Privado de A" not in resp.text

    await pb.delete_record("viajes_personalizados", viaje["id"])
