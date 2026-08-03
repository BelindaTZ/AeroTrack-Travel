from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


# ── RF-RES-006 (CHK008, CHK023) ────────────────────────────────────────────

async def test_crear_alerta_de_precio_queda_activa(client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    await _login(client, usuario)

    resp = await client.post(
        "/alertas-precio",
        data={
            "origen": "jfk",
            "destino": "lax",
            "fecha_objetivo": "2027-08-01",
            "precio_umbral": "150.0",
        },
    )
    assert resp.status_code == 303

    alertas = await ReservasRepository().listar_alertas_de_pasajero(pasajero["id"])
    alerta = next((a for a in alertas if a.get("origen_codigo") == "JFK"), None)
    assert alerta is not None
    assert alerta["activa"] is True
    assert alerta["destino_codigo"] == "LAX"
    assert alerta["precio_umbral"] == 150.0

    await moc.eliminar("alertas_precio", alerta["id"])
