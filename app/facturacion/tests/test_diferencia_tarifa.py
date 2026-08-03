from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def _pagar(client, reserva_id, total_pagar) -> dict:
    resp = await client.post(f"/reservas/{reserva_id}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303
    pago = await FacturacionRepository().pago_exitoso_de_reserva(reserva_id)
    assert pago is not None
    assert pago["monto"] == total_pagar
    return pago


async def _limpiar_pago(pago_id: str, reserva_id: str) -> None:
    repo = FacturacionRepository()
    factura = await repo.factura_de_pago(pago_id)
    if factura is not None:
        await moc.eliminar("facturas", factura["id"])
    comisiones = await repo.listar_comisiones()
    comision = next((c for c in comisiones if c.get("reserva_id") == reserva_id), None)
    if comision is not None:
        await moc.eliminar("comisiones", comision["id"])
    await moc.eliminar("pagos", pago_id)


# ── CHK009: diferencia positiva cobra, negativa reembolsa SOLO la diferencia ──

async def test_diferencia_positiva_genera_cobro_adicional_real(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=150.0)
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=150.0
    )

    await _login(client, usuario)
    pago = await _pagar(client, reserva["id"], 150.0)

    resp = await client.post(
        f"/internal/reservas/{reserva['id']}/diferencia-tarifa", data={"monto_diferencia": 45.0}
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["tipo"] == "cobro"
    assert cuerpo["monto"] == 45.0
    assert cuerpo["estado"] == "exitoso"
    assert cuerpo["stripe_payment_intent_id"].startswith("pi_")

    await moc.eliminar("pagos", cuerpo["id"])
    await _limpiar_pago(pago["id"], reserva["id"])


async def test_diferencia_negativa_reembolsa_solo_la_diferencia_no_el_total(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=300.0)
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=300.0
    )

    facturacion_repo = FacturacionRepository()

    await _login(client, usuario)
    pago = await _pagar(client, reserva["id"], 300.0)

    resp = await client.post(
        f"/internal/reservas/{reserva['id']}/diferencia-tarifa", data={"monto_diferencia": -70.0}
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["tipo"] == "reembolso"
    assert cuerpo["monto"] == 70.0  # SOLO la diferencia, nunca los 300.0 del total
    assert cuerpo["estado"] == "procesado"
    assert cuerpo["stripe_refund_id"].startswith("re_")

    # El pago original sigue como estaba — esto no es una cancelación.
    pago_sin_cambios = await facturacion_repo.obtener_pago(pago["id"])
    assert pago_sin_cambios["estado"] == "exitoso"

    await moc.eliminar("reembolsos", cuerpo["id"])
    await _limpiar_pago(pago["id"], reserva["id"])
