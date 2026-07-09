from urllib.parse import unquote


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


# ── RF-RES-004 / RN-RES-003 (CHK005, CHK012, CHK021) ──────────────────────

async def test_cancelar_bloqueada_si_vuelo_completado(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory(estado="completado")
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada")

    await _login(client, usuario)
    resp = await client.post(f"/reservas/{reserva['id']}/cancelar")
    assert resp.status_code == 303
    assert "No es posible cancelar un vuelo ya realizado" in unquote(resp.headers["location"])

    sin_cambios = await pb.get_record("reservas", reserva["id"])
    assert sin_cambios["estado"] == "confirmada"


# ── RF-RES-004 (CHK006) ────────────────────────────────────────────────────

async def test_cancelar_normal_pasa_a_cancelada_y_registra_reembolso_segun_politica(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory(estado="programado")
    tarifa = await tarifa_factory(vuelo["id"])
    nivel = await pb.get_record("niveles_tarifa", tarifa["nivel_tarifa_id"])
    politica = await pb.get_record("politicas_reembolso", nivel["politica_reembolso_id"])
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=200.0
    )

    await _login(client, usuario)
    # Paga de verdad primero (Stripe test mode real) para que exista un
    # `pagos` exitoso sobre el que Facturación pueda calcular el reembolso —
    # cerrar este punto significa dejar de simularlo, no solo de auditarlo.
    resp_pago = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp_pago.status_code == 303
    pago = await pb.get_first("pagos", f'reserva_id="{reserva["id"]}" && estado="exitoso"')
    assert pago is not None

    resp = await client.post(f"/reservas/{reserva['id']}/cancelar")
    assert resp.status_code == 303

    actualizada = await pb.get_record("reservas", reserva["id"])
    assert actualizada["estado"] == "cancelada"

    registro = await pb.get_first("auditoria", f'accion="cancelar" && registro_id="{reserva["id"]}"')
    assert registro is not None

    reembolso = await pb.get_first("reembolsos", f'reserva_id="{reserva["id"]}"')
    if politica["porcentaje_reembolso"] > 0:
        # Reembolso real vía Stripe test mode — no un marcador de "pendiente".
        assert reembolso is not None
        assert reembolso["estado"] == "procesado"
        assert reembolso["stripe_refund_id"].startswith("re_")
        esperado = round(pago["monto"] * politica["porcentaje_reembolso"] / 100, 2)
        assert reembolso["monto"] == esperado
        assert registro["detalle"]["reembolso_monto"] == esperado

        pago_actualizado = await pb.get_record("pagos", pago["id"])
        assert pago_actualizado["estado"] == "reembolsado"
        await pb.delete_record("reembolsos", reembolso["id"])
    else:
        assert reembolso is None
        assert "estado_reembolso" not in registro["detalle"]

    await pb.delete_record("auditoria", registro["id"])
    factura = await pb.get_first("facturas", f'pago_id="{pago["id"]}"')
    if factura is not None:
        await pb.delete_record("facturas", factura["id"])
    comision = await pb.get_first("comisiones", f'reserva_id="{reserva["id"]}"')
    if comision is not None:
        await pb.delete_record("comisiones", comision["id"])
    await pb.delete_record("pagos", pago["id"])


async def test_cancelar_reserva_ajena_bloqueada(client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, _pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero_a["id"], vuelo["id"], tarifa["id"])

    await _login(client, usuario_b)
    resp = await client.post(f"/reservas/{reserva['id']}/cancelar")
    assert resp.status_code == 303
    assert "Sin permiso" in unquote(resp.headers["location"])
