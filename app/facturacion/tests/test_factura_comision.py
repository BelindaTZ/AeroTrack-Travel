from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def test_pago_exitoso_genera_factura_con_pdf_y_comision_correcta(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=300.0
    )

    repo = FacturacionRepository()

    await _login(client, usuario)
    resp = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303

    pago = await repo.pago_exitoso_de_reserva(reserva["id"])
    assert pago is not None

    factura = await repo.factura_de_pago(pago["id"])
    assert factura is not None
    assert factura["reserva_id"] == reserva["id"]
    assert factura["total"] == 300.0
    assert factura["numero_factura"].startswith("FAC-")
    assert factura["archivo_pdf"]  # nombre de archivo subido, no vacío

    aerolinea = await pb.get_record("aerolineas", vuelo["aerolinea_id"])
    comisiones = await repo.listar_comisiones()
    comision = next((c for c in comisiones if c.get("reserva_id") == reserva["id"]), None)
    assert comision is not None
    assert comision["estado"] == "pendiente_cobro"
    esperado = round(300.0 * aerolinea["comision_pactada_pct"] / 100, 2)
    assert comision["monto"] == esperado

    await moc.eliminar("comisiones", comision["id"])
    await moc.eliminar("facturas", factura["id"])
    await moc.eliminar("pagos", pago["id"])
