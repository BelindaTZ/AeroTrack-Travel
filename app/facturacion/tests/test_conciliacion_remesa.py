import httpx
from httpx import ASGITransport

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.main import app
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def _pagar_como_admin(admin_client, reserva_id) -> tuple[dict, dict]:
    resp = await admin_client.post(f"/reservas/{reserva_id}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303
    repo = FacturacionRepository()
    pago = await repo.pago_exitoso_de_reserva(reserva_id)
    assert pago is not None
    comisiones = await repo.listar_comisiones()
    comision = next((c for c in comisiones if c.get("reserva_id") == reserva_id), None)
    assert comision is not None
    return pago, comision


async def _limpiar_pago(pago_id: str, reserva_id: str) -> None:
    factura = await FacturacionRepository().factura_de_pago(pago_id)
    if factura is not None:
        await moc.eliminar("facturas", factura["id"])
    await moc.eliminar("pagos", pago_id)


# ── CHK004: marcar cobrada actualiza estado+fecha, RBAC, sin reversión ────

async def test_marcar_cobrada_actualiza_estado_y_no_admite_reversion(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")

    repo = FacturacionRepository()
    pago, comision = await _pagar_como_admin(admin_client, reserva["id"])
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

    actualizada = await repo.obtener_comision(comision["id"])
    assert actualizada["estado"] == "cobrada"
    assert actualizada["fecha_cobro_real"]

    # No existe ninguna vía para revertir — un segundo intento es un no-op
    # sobre el mismo estado final, nunca vuelve a pendiente_cobro.
    resp_repetido = await admin_client.post(f"/backoffice/comisiones/{comision['id']}/marcar-cobrada")
    assert resp_repetido.status_code == 303
    sin_cambios = await repo.obtener_comision(comision["id"])
    assert sin_cambios["estado"] == "cobrada"

    await moc.eliminar("comisiones", comision["id"])
    await _limpiar_pago(pago["id"], reserva["id"])


# ── CHK005: la remesa agrupa el monto total correcto de una aerolínea/periodo ──

async def test_generar_remesa_agrupa_monto_total_correcto(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
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

    repo = FacturacionRepository()
    pago_a, comision_a = await _pagar_como_admin(admin_client, reserva_a["id"])
    pago_b, comision_b = await _pagar_como_admin(admin_client, reserva_b["id"])

    await admin_client.post(f"/backoffice/comisiones/{comision_a['id']}/marcar-cobrada")
    await admin_client.post(f"/backoffice/comisiones/{comision_b['id']}/marcar-cobrada")

    resp = await admin_client.post(
        "/backoffice/remesas", data={"aerolinea_id": vuelo["aerolinea_id"], "periodo": "2026-07"}
    )
    assert resp.status_code == 303

    # La base es compartida (datos demo + posibles corridas previas) y
    # `periodo` es un texto libre sin constraint de unicidad — puede haber
    # más de una remesa con la misma (aerolinea_id, periodo). La única
    # identificación confiable de "la remesa que generó ESTE POST" es vía
    # el vínculo real con `comision_a` (recién creada en este test, id
    # único), no buscando por (aerolinea, periodo).
    todos_vinculos = await moc.listar_todos("remesa_comisiones")
    vinculo_de_a = next((v for v in todos_vinculos if v["comision_id"] == comision_a["id"]), None)
    assert vinculo_de_a is not None
    remesa = await repo.obtener_remesa(vinculo_de_a["remesa_id"])
    assert remesa is not None
    assert remesa["aerolinea_id"] == vuelo["aerolinea_id"]
    assert remesa["periodo"] == "2026-07"

    # `comisiones_cobradas_sin_remesa` agrupa por aerolínea sin filtrar por
    # período (ver `facturacion_repo.py`) — en una base compartida con datos
    # demo puede haber otras comisiones "cobrada, sin remesa" legítimas para
    # la misma aerolínea (`scripts/seed_demo_wp10_wp13_wp14.py` deja algunas
    # a propósito para poder generar una remesa nueva desde la UI). Por eso
    # el total esperado se calcula desde los vínculos REALES de la remesa,
    # no asumiendo que solo entraron comision_a/comision_b.
    vinculos = [v for v in todos_vinculos if v.get("remesa_id") == remesa["id"]]
    comision_ids_en_remesa = {v["comision_id"] for v in vinculos}
    assert comision_a["id"] in comision_ids_en_remesa
    assert comision_b["id"] in comision_ids_en_remesa

    montos = [(await repo.obtener_comision(cid))["monto"] for cid in comision_ids_en_remesa]
    esperado = round(sum(montos), 2)
    assert remesa["monto_total"] == esperado

    for v in vinculos:
        await moc.eliminar("remesa_comisiones", v["id"])
    await moc.eliminar("remesas", remesa["id"])
    await moc.eliminar("comisiones", comision_a["id"])
    await moc.eliminar("comisiones", comision_b["id"])
    await _limpiar_pago(pago_a["id"], reserva_a["id"])
    await _limpiar_pago(pago_b["id"], reserva_b["id"])


# ── WP-14 (auditoría de WorkPanels, 2026-07-31) ──────────────────────────

async def test_marcar_remesa_pagada(pb, admin_client, vuelo_factory):
    vuelo = await vuelo_factory()
    repo = FacturacionRepository()
    remesa = await repo.crear_remesa(
        {
            "aerolinea_id": vuelo["aerolinea_id"], "periodo": "2026-06",
            "monto_total": 50.0, "estado": "pendiente",
            "fecha_generacion": "2027-01-01 00:00:00.000Z",
        }
    )
    try:
        resp = await admin_client.post(f"/backoffice/remesas/{remesa['id']}/marcar-pagada", follow_redirects=True)
        assert resp.status_code == 200
        assert "Remesa marcada como pagada" in resp.text

        actualizada = await repo.obtener_remesa(remesa["id"])
        assert actualizada["estado"] == "pagada"

        # ya pagada — no se puede volver a marcar
        resp = await admin_client.post(f"/backoffice/remesas/{remesa['id']}/marcar-pagada", follow_redirects=True)
        assert resp.status_code == 200
        assert "ya estaba pagada" in resp.text
    finally:
        await moc.eliminar("remesas", remesa["id"])


async def test_filtro_estado_y_paginacion_remesas(pb, admin_client, vuelo_factory):
    vuelo = await vuelo_factory()
    repo = FacturacionRepository()
    remesa = await repo.crear_remesa(
        {
            "aerolinea_id": vuelo["aerolinea_id"], "periodo": "2026-05",
            "monto_total": 77.0, "estado": "pagada",
            "fecha_generacion": "2027-01-01 00:00:00.000Z",
        }
    )
    try:
        resp = await admin_client.get("/backoffice/remesas", params={"estado": "pagada"})
        assert resp.status_code == 200
        assert "77.00" in resp.text

        resp = await admin_client.get("/backoffice/remesas", params={"estado": "pendiente"})
        assert resp.status_code == 200
        assert "77.00" not in resp.text
    finally:
        await moc.eliminar("remesas", remesa["id"])


# ── IS-21 (auditoría de informes simples, 2026-08-01) — filtro de aerolínea,
# período y exportar CSV ─────────────────────────────────────────────────

async def test_filtro_aerolinea_y_periodo_remesas(pb, admin_client, vuelo_factory):
    vuelo = await vuelo_factory()
    repo = FacturacionRepository()
    vieja = await repo.crear_remesa(
        {
            "aerolinea_id": vuelo["aerolinea_id"], "periodo": "2020-01",
            "monto_total": 88.0, "estado": "pendiente",
            "fecha_generacion": "2020-01-01 00:00:00.000Z",
        }
    )
    reciente = await repo.crear_remesa(
        {
            "aerolinea_id": vuelo["aerolinea_id"], "periodo": "2027-01",
            "monto_total": 99.0, "estado": "pendiente",
            "fecha_generacion": "2027-01-01 00:00:00.000Z",
        }
    )
    try:
        resp = await admin_client.get(
            "/backoffice/remesas", params={"aerolinea_id": vuelo["aerolinea_id"], "desde": "2025-01-01"}
        )
        assert resp.status_code == 200
        assert "99.00" in resp.text
        assert "88.00" not in resp.text
    finally:
        await moc.eliminar("remesas", vieja["id"])
        await moc.eliminar("remesas", reciente["id"])


async def test_exportar_remesas_csv(pb, admin_client, vuelo_factory):
    vuelo = await vuelo_factory()
    repo = FacturacionRepository()
    remesa = await repo.crear_remesa(
        {
            "aerolinea_id": vuelo["aerolinea_id"], "periodo": "2027-02",
            "monto_total": 123.45, "estado": "pendiente",
            "fecha_generacion": "2027-02-01 00:00:00.000Z",
        }
    )
    try:
        resp = await admin_client.get("/backoffice/remesas/exportar", params={"aerolinea_id": vuelo["aerolinea_id"]})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert resp.text.splitlines()[0] == "fecha_generacion,aerolinea,periodo,monto_total,estado"
        assert "123.45" in resp.text
    finally:
        await moc.eliminar("remesas", remesa["id"])
