from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import get_pocketbase_client


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def _limpiar_documentos_de_pago(pago_id: str, reserva_id: str) -> None:
    """Fase 2 encadena factura+comisión a todo pago exitoso — hay que
    borrarlas antes que el `pagos` por prolijidad de la prueba."""
    repo = FacturacionRepository()
    factura = await repo.factura_de_pago(pago_id)
    if factura is not None:
        await moc.eliminar("facturas", factura["id"])
    comisiones = await repo.listar_comisiones()
    comision = next((c for c in comisiones if c.get("reserva_id") == reserva_id), None)
    if comision is not None:
        await moc.eliminar("comisiones", comision["id"])


# ── RF-FAC-001 (CHK001) ────────────────────────────────────────────────────

async def test_pago_exitoso_marca_pagos_exitoso_y_confirma_reserva_real(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=250.0
    )

    facturacion_repo = FacturacionRepository()

    await _login(client, usuario)
    resp = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303
    assert "Pago exitoso" in resp.headers["location"] or "mensaje" in resp.headers["location"]

    reserva_actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert reserva_actualizada["estado"] == "confirmada"

    pago = await facturacion_repo.pago_exitoso_de_reserva(reserva["id"])
    assert pago is not None
    assert pago["monto"] == 250.0
    assert pago["stripe_payment_intent_id"].startswith("pi_")

    await _limpiar_documentos_de_pago(pago["id"], reserva["id"])
    await moc.eliminar("pagos", pago["id"])


async def test_pago_rechazado_marca_fallido_reserva_sigue_pendiente(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")

    facturacion_repo = FacturacionRepository()

    await _login(client, usuario)
    resp = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "rechazado"})
    assert resp.status_code == 402
    assert "declin" in resp.text.lower() or "rechaz" in resp.text.lower()

    reserva_sin_cambios = await ReservasRepository().obtener_reserva(reserva["id"])
    assert reserva_sin_cambios["estado"] == "pendiente_pago"

    pagos = await facturacion_repo.pagos_de_reserva(reserva["id"])
    pago = next((p for p in pagos if p.get("estado") == "fallido"), None)
    assert pago is not None
    await moc.eliminar("pagos", pago["id"])


# ── RNF-FAC-002 (CHK008 / idempotencia real) ──────────────────────────────

async def test_pago_idempotente_no_genera_segundo_cargo(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
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

    pagos = await FacturacionRepository().pagos_de_reserva(reserva["id"])
    assert len(pagos) == 1

    for p in pagos:
        await _limpiar_documentos_de_pago(p["id"], reserva["id"])
        await moc.eliminar("pagos", p["id"])


# ── ampliación de sesión 2026-08-01 — feature flag pagos.stripe_habilitado ─

async def test_pago_rechazado_si_stripe_deshabilitado(
    client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")

    pb_client = get_pocketbase_client()
    flag = await pb_client.get_first("configuracion_sistema", 'clave="pagos.stripe_habilitado"')
    await pb_client.update_record("configuracion_sistema", flag["id"], {"valor": "false"})
    try:
        await _login(client, usuario)
        resp = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
        assert resp.status_code == 402
        assert "deshabilitados" in resp.text.lower()

        reserva_sin_cambios = await ReservasRepository().obtener_reserva(reserva["id"])
        assert reserva_sin_cambios["estado"] == "pendiente_pago"

        pagos = await FacturacionRepository().pagos_de_reserva(reserva["id"])
        assert pagos == []
    finally:
        await pb_client.update_record("configuracion_sistema", flag["id"], {"valor": "true"})
