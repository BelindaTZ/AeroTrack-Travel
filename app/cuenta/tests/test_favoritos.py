"""RF-CTA-002 — guardar/eliminar favorito de tipo destino/hotel/actividad."""

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303


async def test_guardar_y_listar_favorito(client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    await _login(client, usuario)

    resp = await client.post(
        "/favoritos", data={"tipo": "destino", "producto_ref": "JFK — Nueva York"}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert "JFK" in resp.text

    favoritos = await CuentaRepository().listar_favoritos(pasajero["id"])
    assert len(favoritos) == 1
    for f in favoritos:
        await moc.eliminar("favoritos", f["id"])


async def test_tipo_invalido_no_crea_favorito(client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    await _login(client, usuario)

    resp = await client.post(
        "/favoritos", data={"tipo": "no_valido", "producto_ref": "x"}, follow_redirects=True
    )
    assert resp.status_code == 200

    favoritos = await CuentaRepository().listar_favoritos(pasajero["id"])
    assert favoritos == []


async def test_eliminar_favorito_ajeno_no_lo_borra(client, pasajero_factory):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()

    repo = CuentaRepository()
    favorito = await repo.crear_favorito(pasajero_a["id"], "hotel", "hotel-x", "2027-01-01 00:00:00.000Z")

    await _login(client, usuario_b)
    resp = await client.post(f"/favoritos/{favorito['id']}/eliminar", follow_redirects=True)
    assert resp.status_code == 200

    sigue = await repo.obtener_favorito(favorito["id"])
    assert sigue is not None
    await moc.eliminar("favoritos", favorito["id"])


async def test_eliminar_favorito_propio(client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    repo = CuentaRepository()
    favorito = await repo.crear_favorito(pasajero["id"], "actividad", "act-x", "2027-01-01 00:00:00.000Z")

    await _login(client, usuario)
    resp = await client.post(f"/favoritos/{favorito['id']}/eliminar", follow_redirects=True)
    assert resp.status_code == 200

    favoritos = await repo.listar_favoritos(pasajero["id"])
    assert favoritos == []
