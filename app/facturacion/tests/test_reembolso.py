from app.facturacion.repositories.facturacion_repo import FacturacionRepository
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


async def _nivel_tarifa_id(pb, nombre: str) -> str:
    nivel = await pb.get_first("niveles_tarifa", f'nombre="{nombre}"')
    assert nivel is not None, "seed de niveles_tarifa debe correrse antes de la suite"
    return nivel["id"]


async def test_reembolso_segun_politica_real(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    nivel_standard = await _nivel_tarifa_id(pb, "Standard")  # 50% de reembolso
    tarifa = await tarifa_factory(vuelo["id"], nivel_tarifa_id=nivel_standard, precio_final=200.0)
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=200.0
    )

    facturacion_repo = FacturacionRepository()

    await _login(client, usuario)
    pago = await _pagar(client, reserva["id"])

    resp = await client.post(
        "/internal/reembolsos", data={"reserva_id": reserva["id"], "motivo": "Prueba de reembolso parcial"}
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["estado"] == "procesado"
    assert cuerpo["monto"] == 100.0  # 50% de 200.0
    assert cuerpo["stripe_refund_id"].startswith("re_")

    pago_actualizado = await facturacion_repo.obtener_pago(pago["id"])
    assert pago_actualizado["estado"] == "reembolsado"

    await moc.eliminar("reembolsos", cuerpo["id"])
    await _limpiar_pago(pago["id"], reserva["id"])


async def test_reembolso_fuera_de_politica_no_se_procesa_sin_override(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    nivel_light = await _nivel_tarifa_id(pb, "Light")  # 0% de reembolso
    tarifa = await tarifa_factory(vuelo["id"], nivel_tarifa_id=nivel_light, precio_final=150.0)
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=150.0
    )

    facturacion_repo = FacturacionRepository()

    await _login(client, usuario)
    pago = await _pagar(client, reserva["id"])

    resp = await client.post(
        "/internal/reembolsos", data={"reserva_id": reserva["id"], "motivo": "Intento fuera de política"}
    )
    assert resp.status_code == 422

    # La firma de `procesar_reembolso` no acepta un monto manual — no hay
    # ninguna vía por la que este reembolso pueda materializarse (RN-FAC-001).
    reembolsos = await moc.listar_todos("reembolsos")
    reembolso = next((r for r in reembolsos if r.get("reserva_id") == reserva["id"]), None)
    assert reembolso is None

    pago_sin_cambios = await facturacion_repo.obtener_pago(pago["id"])
    assert pago_sin_cambios["estado"] == "exitoso"

    await _limpiar_pago(pago["id"], reserva["id"])
