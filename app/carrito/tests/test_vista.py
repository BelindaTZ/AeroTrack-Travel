"""RF-CAR-001,002,003,004 (CU-O93-O96) — vista HTML sobre el mismo
`carrito_service.py` que ya prueba `test_carrito.py`/`test_checkout.py`
por debajo del router. Aquí se prueba el camino navegable (formularios +
redirects), no la lógica de negocio (ya cubierta)."""


async def test_ver_carrito_vacio_sin_sesion_no_falla(client):
    resp = await client.get("/carrito/ver")
    # Sin sesión, verificar_sesion redirige a /login (SesionExpirada) — el
    # comportamiento correcto es no reventar con un 500.
    assert resp.status_code in (200, 303)


async def test_agregar_ver_y_eliminar_item(pasajero_client, auto_factory):
    auto = await auto_factory(precio_dia=63.0)

    resp = await pasajero_client.post(
        "/carrito/agregar",
        data={"tipo_producto": "auto", "auto_id": auto["id"], "precio_snapshot": 63.0},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Opel Mokka" in resp.text
    assert "Paris" in resp.text

    ver = await pasajero_client.get("/carrito/ver")
    assert "63.00" in ver.text

    # localizar el item_id real para eliminarlo (no expuesto directo en el HTML)
    from app.carrito.services.carrito_service import ver_carrito

    resultado = await ver_carrito(pasajero_client.pasajero["id"])
    item_id = resultado["items"][0]["id"]

    resp = await pasajero_client.post(f"/carrito/eliminar/{item_id}", follow_redirects=True)
    assert resp.status_code == 200
    assert "Tu carrito está vacío" in resp.text


async def test_confirmar_checkout_crea_reserva_y_muestra_confirmacion(pasajero_client, auto_factory, pb):
    auto = await auto_factory(precio_dia=63.0)
    await pasajero_client.post(
        "/carrito/agregar",
        data={"tipo_producto": "auto", "auto_id": auto["id"], "precio_snapshot": 63.0},
    )

    resp = await pasajero_client.post("/carrito/confirmar")
    assert resp.status_code == 200
    assert "Compra confirmada" in resp.text
    assert "63.00" in resp.text

    reserva = await pb.get_first(
        "reservas", f'pasajero_titular_id="{pasajero_client.pasajero["id"]}"'
    )
    assert reserva is not None
    assert reserva["total_pagar"] == 63.0

    items = await pb.list_records("reserva_items", {"filter": f'reserva_id="{reserva["id"]}"'})
    for item in items["items"]:
        await pb.delete_record("reserva_items", item["id"])
    await pb.delete_record("reservas", reserva["id"])


async def test_confirmar_checkout_vacio_redirige_con_mensaje(pasajero_client):
    resp = await pasajero_client.post("/carrito/confirmar", follow_redirects=True)
    assert resp.status_code == 200
    assert "vacío" in resp.text
