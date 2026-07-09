import httpx
from httpx import ASGITransport

from app.main import app


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def _pagar_como_admin(admin_client, pb, reserva_id) -> tuple[dict, dict]:
    resp = await admin_client.post(f"/reservas/{reserva_id}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303
    pago = await pb.get_first("pagos", f'reserva_id="{reserva_id}" && estado="exitoso"')
    assert pago is not None
    comision = await pb.get_first("comisiones", f'reserva_id="{reserva_id}"')
    assert comision is not None
    return pago, comision


async def _limpiar_pago(pb, pago_id: str, reserva_id: str) -> None:
    factura = await pb.get_first("facturas", f'pago_id="{pago_id}"')
    if factura is not None:
        await pb.delete_record("facturas", factura["id"])
    await pb.delete_record("pagos", pago_id)


# ── CHK004: marcar cobrada actualiza estado+fecha, RBAC, sin reversión ────

async def test_marcar_cobrada_actualiza_estado_y_no_admite_reversion(
    admin_client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")

    pago, comision = await _pagar_como_admin(admin_client, pb, reserva["id"])
    assert comision["estado"] == "pendiente_cobro"

    # RBAC: un pasajero sin rol de backoffice no puede marcar comisiones.
    # Cliente independiente — `admin_client` reutiliza el mismo objeto que
    # `client` (comparten cookies), así que no puede convivir con otra sesión.
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente_pasajero:
        await _login(cliente_pasajero, usuario)
        resp_sin_permiso = await cliente_pasajero.post(
            f"/backoffice/comisiones/{comision['id']}/marcar-cobrada"
        )
        assert resp_sin_permiso.status_code == 403

    resp = await admin_client.post(f"/backoffice/comisiones/{comision['id']}/marcar-cobrada")
    assert resp.status_code == 303

    actualizada = await pb.get_record("comisiones", comision["id"])
    assert actualizada["estado"] == "cobrada"
    assert actualizada["fecha_cobro_real"]

    # No existe ninguna vía para revertir — un segundo intento es un no-op
    # sobre el mismo estado final, nunca vuelve a pendiente_cobro.
    resp_repetido = await admin_client.post(f"/backoffice/comisiones/{comision['id']}/marcar-cobrada")
    assert resp_repetido.status_code == 303
    sin_cambios = await pb.get_record("comisiones", comision["id"])
    assert sin_cambios["estado"] == "cobrada"

    await pb.delete_record("comisiones", comision["id"])
    await _limpiar_pago(pb, pago["id"], reserva["id"])


# ── CHK005: la remesa agrupa el monto total correcto de una aerolínea/periodo ──

async def test_generar_remesa_agrupa_monto_total_correcto(
    admin_client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()  # misma aerolínea "activa=true" para ambas reservas
    tarifa_a = await tarifa_factory(vuelo["id"], precio_final=200.0)
    tarifa_b = await tarifa_factory(vuelo["id"], precio_final=300.0)
    reserva_a = await reserva_factory(
        pasajero_a["id"], vuelo["id"], tarifa_a["id"], estado="pendiente_pago", total_pagar=200.0
    )
    reserva_b = await reserva_factory(
        pasajero_b["id"], vuelo["id"], tarifa_b["id"], estado="pendiente_pago", total_pagar=300.0
    )

    pago_a, comision_a = await _pagar_como_admin(admin_client, pb, reserva_a["id"])
    pago_b, comision_b = await _pagar_como_admin(admin_client, pb, reserva_b["id"])

    await admin_client.post(f"/backoffice/comisiones/{comision_a['id']}/marcar-cobrada")
    await admin_client.post(f"/backoffice/comisiones/{comision_b['id']}/marcar-cobrada")

    resp = await admin_client.post(
        "/backoffice/remesas", data={"aerolinea_id": vuelo["aerolinea_id"], "periodo": "2026-07"}
    )
    assert resp.status_code == 303

    remesa = await pb.get_first(
        "remesas", f'aerolinea_id="{vuelo["aerolinea_id"]}" && periodo="2026-07"'
    )
    assert remesa is not None
    comision_a_actualizada = await pb.get_record("comisiones", comision_a["id"])
    comision_b_actualizada = await pb.get_record("comisiones", comision_b["id"])
    esperado = round(comision_a_actualizada["monto"] + comision_b_actualizada["monto"], 2)
    assert remesa["monto_total"] == esperado

    vinculos = await pb.list_records("remesa_comisiones", {"filter": f'remesa_id="{remesa["id"]}"'})
    comision_ids_en_remesa = {v["comision_id"] for v in vinculos["items"]}
    assert comision_a["id"] in comision_ids_en_remesa
    assert comision_b["id"] in comision_ids_en_remesa

    for v in vinculos["items"]:
        await pb.delete_record("remesa_comisiones", v["id"])
    await pb.delete_record("remesas", remesa["id"])
    await pb.delete_record("comisiones", comision_a["id"])
    await pb.delete_record("comisiones", comision_b["id"])
    await _limpiar_pago(pb, pago_a["id"], reserva_a["id"])
    await _limpiar_pago(pb, pago_b["id"], reserva_b["id"])
