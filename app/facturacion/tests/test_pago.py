async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def _limpiar_documentos_de_pago(pb, pago_id: str, reserva_id: str) -> None:
    """Fase 2 encadena factura+comisión a todo pago exitoso — hay que
    borrarlas antes que el `pagos` porque `facturas.pago_id` es una
    relación requerida sin cascadeDelete."""
    factura = await pb.get_first("facturas", f'pago_id="{pago_id}"')
    if factura is not None:
        await pb.delete_record("facturas", factura["id"])
    comision = await pb.get_first("comisiones", f'reserva_id="{reserva_id}"')
    if comision is not None:
        await pb.delete_record("comisiones", comision["id"])


# ── RF-FAC-001 (CHK001) ────────────────────────────────────────────────────

async def test_pago_exitoso_marca_pagos_exitoso_y_confirma_reserva_real(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=250.0
    )

    await _login(client, usuario)
    resp = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303
    assert "Pago exitoso" in resp.headers["location"] or "mensaje" in resp.headers["location"]

    reserva_actualizada = await pb.get_record("reservas", reserva["id"])
    assert reserva_actualizada["estado"] == "confirmada"

    pago = await pb.get_first("pagos", f'reserva_id="{reserva["id"]}" && estado="exitoso"')
    assert pago is not None
    assert pago["monto"] == 250.0
    assert pago["stripe_payment_intent_id"].startswith("pi_")

    await _limpiar_documentos_de_pago(pb, pago["id"], reserva["id"])
    await pb.delete_record("pagos", pago["id"])


async def test_pago_rechazado_marca_fallido_reserva_sigue_pendiente(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")

    await _login(client, usuario)
    resp = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "rechazado"})
    assert resp.status_code == 402
    assert "declin" in resp.text.lower() or "rechaz" in resp.text.lower()

    reserva_sin_cambios = await pb.get_record("reservas", reserva["id"])
    assert reserva_sin_cambios["estado"] == "pendiente_pago"

    pago = await pb.get_first("pagos", f'reserva_id="{reserva["id"]}" && estado="fallido"')
    assert pago is not None
    await pb.delete_record("pagos", pago["id"])


# ── RNF-FAC-002 (CHK008 / idempotencia real) ──────────────────────────────

async def test_pago_idempotente_no_genera_segundo_cargo(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")

    await _login(client, usuario)
    await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    # Segundo intento sobre la misma reserva ya pagada — no debe crear un
    # segundo registro en `pagos` (el servicio corta antes de llamar a Stripe).
    resp2 = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp2.status_code == 303

    pagos = await pb.list_records("pagos", {"filter": f'reserva_id="{reserva["id"]}"'})
    assert pagos["totalItems"] == 1

    for p in pagos["items"]:
        await _limpiar_documentos_de_pago(pb, p["id"], reserva["id"])
        await pb.delete_record("pagos", p["id"])
