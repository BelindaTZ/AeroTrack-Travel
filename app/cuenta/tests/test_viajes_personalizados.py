"""RF-CTA-004 — crear/eliminar viaje personalizado (planificación libre)."""

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303


async def test_crear_viaje_personalizado(client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    await _login(client, usuario)

    resp = await client.post(
        "/viajes-personalizados", data={"nombre": "Luna de miel", "descripcion": "Presupuesto ideas"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Luna de miel" in resp.text

    viajes = await CuentaRepository().listar_viajes_personalizados(pasajero["id"])
    assert len(viajes) == 1
    for v in viajes:
        await moc.eliminar("viajes_personalizados", v["id"])


async def test_eliminar_viaje_personalizado(client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    repo = CuentaRepository()
    viaje = await repo.crear_viaje_personalizado(pasajero["id"], "Viaje a borrar", "")

    await _login(client, usuario)
    resp = await client.post(f"/viajes-personalizados/{viaje['id']}/eliminar", follow_redirects=True)
    assert resp.status_code == 200

    viajes = await repo.listar_viajes_personalizados(pasajero["id"])
    assert viajes == []


async def test_no_ve_viajes_de_otro_pasajero(client, pasajero_factory):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()
    repo = CuentaRepository()
    viaje = await repo.crear_viaje_personalizado(pasajero_a["id"], "Privado de A", "")

    await _login(client, usuario_b)
    resp = await client.get("/viajes-personalizados")
    assert resp.status_code == 200
    assert "Privado de A" not in resp.text

    await moc.eliminar("viajes_personalizados", viaje["id"])
