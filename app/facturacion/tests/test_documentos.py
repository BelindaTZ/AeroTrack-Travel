async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def _pagar(client, pb, reserva_id) -> dict:
    resp = await client.post(f"/reservas/{reserva_id}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303
    pago = await pb.get_first("pagos", f'reserva_id="{reserva_id}" && estado="exitoso"')
    assert pago is not None
    return pago


async def _limpiar(pb, pago_id: str, reserva_id: str) -> None:
    factura = await pb.get_first("facturas", f'pago_id="{pago_id}"')
    if factura is not None:
        await pb.delete_record("facturas", factura["id"])
    comision = await pb.get_first("comisiones", f'reserva_id="{reserva_id}"')
    if comision is not None:
        await pb.delete_record("comisiones", comision["id"])
    await pb.delete_record("pagos", pago_id)


async def test_historial_solo_muestra_pagos_propios(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa_a = await tarifa_factory(vuelo["id"])
    reserva_a = await reserva_factory(pasajero_a["id"], vuelo["id"], tarifa_a["id"])

    await _login(client, usuario_a)
    pago_a = await _pagar(client, pb, reserva_a["id"])

    await _login(client, usuario_b)
    resp = await client.get("/pagos")
    assert resp.status_code == 200
    assert reserva_a["codigo_reserva"] not in resp.text

    await _limpiar(pb, pago_a["id"], reserva_a["id"])


async def test_descarga_factura_ajena_da_404(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, _pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero_a["id"], vuelo["id"], tarifa["id"])

    await _login(client, usuario_a)
    pago = await _pagar(client, pb, reserva["id"])
    factura = await pb.get_first("facturas", f'pago_id="{pago["id"]}"')
    assert factura is not None

    # El propio dueño sí puede descargarla.
    resp_propia = await client.get(f"/facturas/{factura['id']}/pdf")
    assert resp_propia.status_code == 200
    assert resp_propia.headers["content-type"] == "application/pdf"

    await _login(client, usuario_b)
    resp_ajena = await client.get(f"/facturas/{factura['id']}/pdf")
    assert resp_ajena.status_code == 404

    await _limpiar(pb, pago["id"], reserva["id"])


async def test_descarga_itinerario_propio_y_ajeno(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, _pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(
        pasajero_a["id"], vuelo["id"], tarifa["id"], estado="confirmada"
    )

    await _login(client, usuario_a)
    resp_propio = await client.get(f"/reservas/{reserva['id']}/itinerario-pdf")
    assert resp_propio.status_code == 200
    assert resp_propio.headers["content-type"] == "application/pdf"

    await _login(client, usuario_b)
    resp_ajeno = await client.get(f"/reservas/{reserva['id']}/itinerario-pdf")
    assert resp_ajeno.status_code == 404
