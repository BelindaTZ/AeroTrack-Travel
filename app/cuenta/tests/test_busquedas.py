"""RF-CTA-003/RN-CTA-001 — cada módulo de producto escribe su propia
búsqueda (`registrar_busqueda_reciente`); Cuenta solo lee y relanza."""

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303


async def test_buscar_vuelos_logueado_registra_busqueda_reciente(client, pasajero_factory, vuelo_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    await _login(client, usuario)

    resp = await client.get(
        "/vuelos/buscar", params={"origen": "JFK", "destino": "LAX", "fecha": "2027-01-01", "pasajeros": 1}
    )
    assert resp.status_code == 200

    busquedas = [
        b for b in await CuentaRepository().listar_busquedas_recientes(pasajero["id"], limite=500)
        if b.get("tipo_producto") == "vuelo"
    ]
    assert len(busquedas) == 1
    assert busquedas[0]["criterios"]["destino"] == "LAX"

    for b in busquedas:
        await moc.eliminar("busquedas_recientes", b["id"])


async def test_buscar_anonimo_no_registra_busqueda(client, vuelo_factory):
    await vuelo_factory()
    antes = len(await moc.listar_todos("busquedas_recientes"))

    resp = await client.get(
        "/vuelos/buscar", params={"origen": "JFK", "destino": "LAX", "fecha": "2027-01-01"}
    )
    assert resp.status_code == 200

    despues = len(await moc.listar_todos("busquedas_recientes"))
    assert despues == antes


async def test_listar_y_relanzar_busqueda_reciente(client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    id_ = moc.generar_id()
    busqueda = await moc.crear(
        "busquedas_recientes",
        id_,
        {
            "id": id_,
            "pasajero_id": pasajero["id"], "tipo_producto": "hotel",
            "criterios": {"ciudad": "Miami", "checkin": "", "checkout": "", "huespedes": 2},
            "fecha": "2027-01-01 00:00:00.000Z",
        },
    )

    await _login(client, usuario)
    resp = await client.get("/mis-busquedas-recientes")
    assert resp.status_code == 200
    assert "Miami" in resp.text

    resp = await client.post(f"/mis-busquedas-recientes/{busqueda['id']}/relanzar")
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/hoteles/buscar?")
    assert "Miami" in resp.headers["location"]

    await moc.eliminar("busquedas_recientes", busqueda["id"])
