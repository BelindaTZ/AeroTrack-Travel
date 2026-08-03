"""IS-20 (auditoría de informes simples, sesión 2026-08-01) — resumen de
comisiones pendientes de cobro agrupado por aerolínea: filtro de período,
paginación del detalle y exportar CSV. La creación de una comisión real pasa
por el flujo de pago (`_pagar_como_admin`, mismo patrón que
`test_conciliacion_remesa.py`) porque no hay una vía directa de "crear
comisión" fuera de ese flujo."""

import httpx
from httpx import ASGITransport

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.router_backoffice import _comisiones_filtradas, _resumen_por_aerolinea
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


async def test_resumen_agrupa_por_aerolinea_y_respeta_periodo(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")
    pago, comision = await _pagar_como_admin(admin_client, reserva["id"])

    try:
        comisiones_out, _aerolineas, nombre_por_id = await _comisiones_filtradas(None, None, None, None)
        pendientes = [c for c in comisiones_out if c["estado"] == "pendiente_cobro"]
        resumen = _resumen_por_aerolinea(pendientes, nombre_por_id)

        fila = next(r for r in resumen if r["aerolinea_id"] == comision["aerolinea_id"])
        assert fila["numero_reservas"] >= 1
        assert fila["monto_acumulado"] >= comision["monto"]
        assert fila["estado"] == "pendiente_cobro"
        assert fila["dias_transcurridos"] >= 0

        # ordenado por monto acumulado descendente por defecto (IS-20).
        montos = [r["monto_acumulado"] for r in resumen]
        assert montos == sorted(montos, reverse=True)

        # un `desde` futuro excluye la comisión recién creada del período.
        comisiones_futuro, _a2, _n2 = await _comisiones_filtradas(None, None, "2099-01-01", None)
        assert not any(c["id"] == comision["id"] for c in comisiones_futuro)

        # un `hasta` futuro sí la incluye.
        comisiones_hasta, _a3, _n3 = await _comisiones_filtradas(None, None, None, "2099-01-01")
        assert any(c["id"] == comision["id"] for c in comisiones_hasta)
    finally:
        await moc.eliminar("comisiones", comision["id"])
        await _limpiar_pago(pago["id"], reserva["id"])


async def test_backoffice_comisiones_paginacion(admin_client):
    resp = await admin_client.get("/backoffice/comisiones?page=1")
    assert resp.status_code == 200

    resp = await admin_client.get("/backoffice/comisiones?page=999")
    assert resp.status_code == 200


async def test_exportar_comisiones_csv(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")
    pago, comision = await _pagar_como_admin(admin_client, reserva["id"])

    try:
        resp = await admin_client.get("/backoffice/comisiones/exportar")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "attachment" in resp.headers["content-disposition"]
        assert resp.text.splitlines()[0] == (
            "aerolinea,numero_reservas,fecha_devengo,monto_acumulado,dias_transcurridos,estado"
        )
    finally:
        await moc.eliminar("comisiones", comision["id"])
        await _limpiar_pago(pago["id"], reserva["id"])


async def test_exportar_comisiones_bloqueado_sin_permiso(pasajero_factory):
    usuario, _pasajero = await pasajero_factory()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente_pasajero:
        await _login(cliente_pasajero, usuario)
        resp = await cliente_pasajero.get("/backoffice/comisiones/exportar")
        assert resp.status_code == 403
