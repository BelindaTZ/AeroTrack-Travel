"""IS-24 (auditoría de informes simples, sesión 2026-08-01) — reembolsos
procesados por período, con filtro de motivo/estado/tipo de producto y
exportar CSV. La colección real es `reembolsos` (dedicada), no
`pagos.tipo="reembolso"` como sugería el encargo original — confirmado
antes de implementar (ver nota en `router_backoffice.py`). El reembolso de
prueba se crea directo por repo (no vía `/internal/reembolsos`) porque acá
solo importa la lectura/filtrado, no el cálculo de política — eso ya lo
cubre `test_reembolso.py`."""

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.shared import minio_operational_client as moc


async def _crear_reembolso(reserva_id: str, **extra) -> dict:
    data = {
        "reserva_id": reserva_id, "pago_id": "pago-test", "politica_aplicada_id": "politica-test",
        "motivo": "Prueba de informe", "monto": 50.0, "estado": "procesado",
        "stripe_refund_id": "re_test", "fecha_solicitud": "2027-01-01 00:00:00.000Z",
        "fecha_procesado": "2027-01-01 00:00:00.000Z",
    }
    data.update(extra)
    return await FacturacionRepository().crear_reembolso(data)


async def test_filtro_por_estado(admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])
    procesado = await _crear_reembolso(reserva["id"], estado="procesado", motivo="motivo-procesado-test")
    rechazado = await _crear_reembolso(reserva["id"], estado="rechazado", motivo="motivo-rechazado-test")

    try:
        resp = await admin_client.get("/backoffice/reembolsos?estado=procesado")
        assert resp.status_code == 200
        assert "motivo-procesado-test" in resp.text
        assert "motivo-rechazado-test" not in resp.text
    finally:
        await moc.eliminar("reembolsos", procesado["id"])
        await moc.eliminar("reembolsos", rechazado["id"])


async def test_filtro_por_periodo(admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])
    viejo = await _crear_reembolso(reserva["id"], motivo="motivo-viejo-test", fecha_solicitud="2020-01-01 00:00:00.000Z")
    reciente = await _crear_reembolso(reserva["id"], motivo="motivo-reciente-test", fecha_solicitud="2027-01-01 00:00:00.000Z")

    try:
        resp = await admin_client.get("/backoffice/reembolsos?desde=2025-01-01")
        assert resp.status_code == 200
        assert "motivo-reciente-test" in resp.text
        assert "motivo-viejo-test" not in resp.text
    finally:
        await moc.eliminar("reembolsos", viejo["id"])
        await moc.eliminar("reembolsos", reciente["id"])


async def test_filtro_por_tipo_producto(admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])
    reembolso = await _crear_reembolso(reserva["id"], motivo="motivo-tipo-test")

    try:
        resp = await admin_client.get("/backoffice/reembolsos?tipo_producto=vuelo")
        assert resp.status_code == 200
        assert "motivo-tipo-test" in resp.text

        resp_otro = await admin_client.get("/backoffice/reembolsos?tipo_producto=hotel")
        assert "motivo-tipo-test" not in resp_otro.text
    finally:
        await moc.eliminar("reembolsos", reembolso["id"])


async def test_paginacion(admin_client):
    resp = await admin_client.get("/backoffice/reembolsos?page=1")
    assert resp.status_code == 200

    resp = await admin_client.get("/backoffice/reembolsos?page=999")
    assert resp.status_code == 200


async def test_exportar_csv(admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])
    reembolso = await _crear_reembolso(reserva["id"], motivo="motivo-export-test")

    try:
        resp = await admin_client.get("/backoffice/reembolsos/exportar")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert resp.text.splitlines()[0] == "fecha_solicitud,codigo_reserva,pasajero,motivo,monto,estado"
        assert "motivo-export-test" in resp.text
        assert reserva["codigo_reserva"] in resp.text
    finally:
        await moc.eliminar("reembolsos", reembolso["id"])


async def test_exportar_bloqueado_sin_permiso(pasajero_factory):
    import httpx
    from httpx import ASGITransport

    from app.main import app

    usuario, _pasajero = await pasajero_factory()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente_pasajero:
        resp_login = await cliente_pasajero.post(
            "/login", data={"email": usuario["email"], "password": usuario["_password"]}
        )
        assert resp_login.status_code == 303
        resp = await cliente_pasajero.get("/backoffice/reembolsos/exportar")
        assert resp.status_code == 403
