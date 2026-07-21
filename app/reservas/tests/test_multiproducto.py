"""Reservas multi-producto creadas vía Carrito (sin `vuelo_id`) —
`construir_detalle`/`ReservaDetalleOut` dejaron de asumir que toda reserva
tiene un componente de vuelo (2026-07-19). Antes de este arreglo, tanto
`GET /reservas/{id}` como `GET /reservas` ("Mis reservas") reventaban con
un 500 apenas el pasajero tuviera una reserva de solo un producto que no
fuera un vuelo (ej. un auto comprado vía Carrito)."""

from app.carrito.services.carrito_service import agregar_item, confirmar_checkout


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def _crear_auto(pb) -> dict:
    return await pb.create_record(
        "autos_catalogo",
        {
            "proveedor_agregador": "expedia", "marca": "", "modelo": "Opel Mokka",
            "categoria": "SUV", "transmision": "Automatic", "ciudad_recogida": "Paris",
            "aeropuerto_codigo": "CDG", "precio_dia": 63.0, "moneda": "USD",
            "modalidad_pago_disponible": "pagar_al_recoger", "fuente_oferta_ref": "token-test",
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        },
    )


async def test_detalle_reserva_solo_auto_no_revienta(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    auto = await _crear_auto(pb)

    await agregar_item(pasajero["id"], "auto", {"auto_id": auto["id"]}, precio_snapshot=63.0)
    reserva = await confirmar_checkout(pasajero["id"])

    await _login(client, usuario)
    resp = await client.get(f"/reservas/{reserva['id']}")
    assert resp.status_code == 200
    assert reserva["codigo_reserva"] in resp.text
    assert "Opel Mokka" in resp.text
    assert "auto" in resp.text

    reserva_items = await pb.list_records("reserva_items", {"filter": f'reserva_id="{reserva["id"]}"'})
    for ri in reserva_items["items"]:
        await pb.delete_record("reserva_items", ri["id"])
    await pb.delete_record("reservas", reserva["id"])
    await pb.delete_record("autos_catalogo", auto["id"])


async def test_mis_reservas_no_revienta_con_reserva_multiproducto(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    auto = await _crear_auto(pb)

    await agregar_item(pasajero["id"], "auto", {"auto_id": auto["id"]}, precio_snapshot=63.0)
    reserva = await confirmar_checkout(pasajero["id"])

    await _login(client, usuario)
    resp = await client.get("/reservas")
    assert resp.status_code == 200
    assert reserva["codigo_reserva"] in resp.text

    reserva_items = await pb.list_records("reserva_items", {"filter": f'reserva_id="{reserva["id"]}"'})
    for ri in reserva_items["items"]:
        await pb.delete_record("reserva_items", ri["id"])
    await pb.delete_record("reservas", reserva["id"])
    await pb.delete_record("autos_catalogo", auto["id"])
