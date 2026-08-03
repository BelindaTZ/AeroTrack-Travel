"""WP-15 (auditoría de WorkPanels, 2026-08-01) — panel de solo lectura de
Pagos y Facturas, antes inexistente."""

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.shared import minio_operational_client as moc


async def _limpiar_documentos_de_pago(pago_id: str, reserva_id: str) -> None:
    repo = FacturacionRepository()
    factura = await repo.factura_de_pago(pago_id)
    if factura is not None:
        await moc.eliminar("facturas", factura["id"])
    comisiones = await repo.listar_comisiones()
    comision = next((c for c in comisiones if c.get("reserva_id") == reserva_id), None)
    if comision is not None:
        await moc.eliminar("comisiones", comision["id"])


async def test_listar_pagos_con_filtros(admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=175.0)

    resp = await admin_client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303

    repo = FacturacionRepository()
    pago = await repo.pago_exitoso_de_reserva(reserva["id"])
    assert pago is not None

    try:
        resp = await admin_client.get("/backoffice/pagos", params={"codigo_reserva": reserva["codigo_reserva"]})
        assert resp.status_code == 200
        assert reserva["codigo_reserva"] in resp.text
        assert "175.00" in resp.text

        resp = await admin_client.get("/backoffice/pagos", params={"estado": "fallido"})
        assert resp.status_code == 200
        assert reserva["codigo_reserva"] not in resp.text

        resp = await admin_client.get("/backoffice/pagos", params={"nombre_pasajero": "no existe nadie con este nombre"})
        assert resp.status_code == 200
        assert reserva["codigo_reserva"] not in resp.text
    finally:
        await _limpiar_documentos_de_pago(pago["id"], reserva["id"])
        await moc.eliminar("pagos", pago["id"])


async def test_listar_facturas_con_filtros(admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=210.0)

    resp = await admin_client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303

    repo = FacturacionRepository()
    pago = await repo.pago_exitoso_de_reserva(reserva["id"])
    factura = await repo.factura_de_pago(pago["id"])
    assert factura is not None

    try:
        resp = await admin_client.get("/backoffice/facturas", params={"codigo_reserva": reserva["codigo_reserva"]})
        assert resp.status_code == 200
        assert factura["numero_factura"] in resp.text
        assert "210.00" in resp.text

        resp = await admin_client.get("/backoffice/facturas", params={"codigo_reserva": "XX-NO-EXISTE-XX"})
        assert resp.status_code == 200
        assert factura["numero_factura"] not in resp.text
    finally:
        await _limpiar_documentos_de_pago(pago["id"], reserva["id"])
        await moc.eliminar("pagos", pago["id"])


async def test_pasajero_no_tiene_acceso_a_pagos_ni_facturas(client, usuario_factory):
    pasajero = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})
    resp = await client.get("/backoffice/pagos", headers={"Accept": "application/json"})
    assert resp.status_code == 403
    resp = await client.get("/backoffice/facturas", headers={"Accept": "application/json"})
    assert resp.status_code == 403
