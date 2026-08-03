from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def _pagar(client, reserva_id) -> dict:
    resp = await client.post(f"/reservas/{reserva_id}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303
    pago = await FacturacionRepository().pago_exitoso_de_reserva(reserva_id)
    assert pago is not None
    return pago


async def _limpiar(pago_id: str, reserva_id: str) -> None:
    repo = FacturacionRepository()
    factura = await repo.factura_de_pago(pago_id)
    if factura is not None:
        await moc.eliminar("facturas", factura["id"])
    comisiones = await repo.listar_comisiones()
    comision = next((c for c in comisiones if c.get("reserva_id") == reserva_id), None)
    if comision is not None:
        await moc.eliminar("comisiones", comision["id"])
    await moc.eliminar("pagos", pago_id)


async def test_historial_solo_muestra_pagos_propios(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa_a = await tarifa_factory(vuelo["id"])
    reserva_a = await reserva_factory(pasajero_a["id"], vuelo["id"], tarifa_a["id"])

    await _login(client, usuario_a)
    pago_a = await _pagar(client, reserva_a["id"])

    await _login(client, usuario_b)
    resp = await client.get("/pagos")
    assert resp.status_code == 200
    assert reserva_a["codigo_reserva"] not in resp.text

    await _limpiar(pago_a["id"], reserva_a["id"])


async def test_descarga_factura_ajena_da_404(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, _pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero_a["id"], vuelo["id"], tarifa["id"])

    await _login(client, usuario_a)
    pago = await _pagar(client, reserva["id"])
    factura = await FacturacionRepository().factura_de_pago(pago["id"])
    assert factura is not None

    # El propio dueño sí puede descargarla.
    resp_propia = await client.get(f"/facturas/{factura['id']}/pdf")
    assert resp_propia.status_code == 200
    assert resp_propia.headers["content-type"] == "application/pdf"

    await _login(client, usuario_b)
    resp_ajena = await client.get(f"/facturas/{factura['id']}/pdf")
    assert resp_ajena.status_code == 404

    await _limpiar(pago["id"], reserva["id"])


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


# ── RF-RES-009 (voucher persistido, mismo patrón que facturas.archivo_pdf) ──

async def test_pago_exitoso_genera_voucher_persistido(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])

    await _login(client, usuario)
    pago = await _pagar(client, reserva["id"])

    actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert actualizada["voucher_pdf"]

    await _limpiar(pago["id"], reserva["id"])


async def test_descarga_voucher_propio_y_ajeno(
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
    resp_propio = await client.get(f"/reservas/{reserva['id']}/voucher-pdf")
    assert resp_propio.status_code == 200
    assert resp_propio.headers["content-type"] == "application/pdf"

    await _login(client, usuario_b)
    resp_ajeno = await client.get(f"/reservas/{reserva['id']}/voucher-pdf")
    assert resp_ajeno.status_code == 404


async def test_voucher_se_autogenera_si_la_reserva_no_lo_tenia(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    """Reserva confirmada por otra vía (p. ej. datos de antes de este RF) sin
    voucher_pdf todavía — la descarga lo genera y lo persiste, en vez de fallar."""
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada"
    )
    assert not reserva.get("voucher_pdf")

    await _login(client, usuario)
    resp = await client.get(f"/reservas/{reserva['id']}/voucher-pdf")
    assert resp.status_code == 200

    actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert actualizada["voucher_pdf"]
