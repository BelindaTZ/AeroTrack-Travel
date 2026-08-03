"""IS-05 (auditoría de informes simples, sesión 2026-08-01) — reporte de
pasajeros nuevos por período/canal (ya existía, CU-T05/CU-T37): paginación
25/página, columna `tiene_reserva` y exportar CSV agregados sobre el reporte
existente. `canal_registro`/`frecuencia_min`/`destino` ya estaban probados
en producción antes de esta sesión, no se reprueban aquí."""

import httpx
from httpx import ASGITransport

from app.main import app
from app.pasajeros.router_backoffice import _reporte_pasajeros_filtrado


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def test_tiene_reserva_refleja_si_el_pasajero_tiene_reservas(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario_con, pasajero_con = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    await reserva_factory(pasajero_con["id"], vuelo["id"], tarifa["id"])

    usuario_sin, pasajero_sin = await pasajero_factory()

    filas = await _reporte_pasajeros_filtrado(None, None, None, None, None)
    por_email = {f["email"]: f for f in filas}

    assert por_email[usuario_con["email"]]["num_reservas"] >= 1
    assert por_email[usuario_sin["email"]]["num_reservas"] == 0


async def test_backoffice_pasajeros_reporte_paginacion(admin_client):
    resp = await admin_client.get("/backoffice/pasajeros/reporte?page=1")
    assert resp.status_code == 200

    resp = await admin_client.get("/backoffice/pasajeros/reporte?page=999")
    assert resp.status_code == 200


async def test_exportar_pasajeros_csv(admin_client, pasajero_factory):
    usuario, _pasajero = await pasajero_factory()

    resp = await admin_client.get("/backoffice/pasajeros/reporte/exportar")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.text.splitlines()[0] == (
        "nombre_completo,email,fecha_registro,canal_registro,num_reservas,tiene_reserva,destinos"
    )
    assert usuario["email"] in resp.text


async def test_exportar_pasajeros_bloqueado_sin_permiso(pasajero_factory):
    usuario, _pasajero = await pasajero_factory()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente_pasajero:
        await _login(cliente_pasajero, usuario)
        resp = await cliente_pasajero.get("/backoffice/pasajeros/reporte/exportar")
        assert resp.status_code == 403
