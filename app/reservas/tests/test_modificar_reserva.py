from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


# ── RF-RES-003 / RN-RES-002 (CHK004, CHK011, CHK020, CHK026) ─────────────

async def test_modificar_cambia_tarifa_cobra_la_diferencia_exacta_de_verdad(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa_original = await tarifa_factory(vuelo["id"], precio_final=200.0, cupos_disponibles=5)
    tarifa_nueva = await tarifa_factory(vuelo["id"], precio_final=280.0, cupos_disponibles=5)
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa_original["id"], estado="pendiente_pago", total_pagar=200.0
    )

    facturacion_repo = FacturacionRepository()

    await _login(client, usuario)
    # Paga de verdad primero (Stripe test mode real) — sin un pago original no
    # hay contra qué cobrar/reembolsar la diferencia.
    resp_pago = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp_pago.status_code == 303
    pago_original = await facturacion_repo.pago_exitoso_de_reserva(reserva["id"])
    assert pago_original is not None

    resp = await client.put(
        f"/reservas/{reserva['id']}",
        data={"nueva_tarifa_id": tarifa_nueva["id"]},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estado"] == "modificada"
    assert data["total_pagar"] == 280.0

    registro = await pb.get_first("auditoria", f'accion="modificar" && registro_id="{reserva["id"]}"')
    assert registro is not None
    assert registro["detalle"]["diferencia_tarifa"] == 80.0
    assert registro["detalle"]["diferencia_tipo"] == "cobro"
    pago_diferencia_id = registro["detalle"]["diferencia_registro_id"]
    await pb.delete_record("auditoria", registro["id"])

    # Cobro real de la diferencia — un `pagos` nuevo, separado del original,
    # nunca el total de la reserva.
    pago_diferencia = await facturacion_repo.obtener_pago(pago_diferencia_id)
    assert pago_diferencia["estado"] == "exitoso"
    assert pago_diferencia["monto"] == 80.0
    assert pago_diferencia["stripe_payment_intent_id"].startswith("pi_")

    tarifa_original_actualizada = await moc.obtener("cupos_tarifas_vuelo", tarifa_original["id"])
    assert tarifa_original_actualizada["cupos_disponibles"] == 6  # cupo anterior liberado

    await moc.eliminar("pagos", pago_diferencia["id"])
    factura = await facturacion_repo.factura_de_pago(pago_original["id"])
    if factura is not None:
        await moc.eliminar("facturas", factura["id"])
    comisiones = await facturacion_repo.listar_comisiones()
    comision = next((c for c in comisiones if c.get("reserva_id") == reserva["id"]), None)
    if comision is not None:
        await moc.eliminar("comisiones", comision["id"])
    await moc.eliminar("pagos", pago_original["id"])


async def test_modificar_sin_cambio_de_precio_no_dispara_diferencia(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=200.0)
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada", total_pagar=200.0
    )

    await _login(client, usuario)
    resp = await client.put(
        f"/reservas/{reserva['id']}",
        data={"nueva_tarifa_id": tarifa["id"]},  # misma tarifa -> sin cambio real
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200

    registro = await pb.get_first("auditoria", f'accion="modificar" && registro_id="{reserva["id"]}"')
    assert registro is None  # RN-RES-002: nada se dispara si el precio no cambió


# ── CHK003 ──────────────────────────────────────────────────────────────

async def test_modificar_reserva_cancelada_bloqueada(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    tarifa_nueva = await tarifa_factory(vuelo["id"], precio_final=300.0)
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="cancelada")

    await _login(client, usuario)
    resp = await client.put(
        f"/reservas/{reserva['id']}",
        data={"nueva_tarifa_id": tarifa_nueva["id"]},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 409
