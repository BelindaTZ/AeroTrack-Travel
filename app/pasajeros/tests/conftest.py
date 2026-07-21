# Fixtures compartidas (client, pb, usuario_factory, vuelo_factory,
# tarifa_factory, pasajero_factory, reserva_factory, admin_client,
# rol_administrador, rol_agente) viven en el conftest.py de la raíz del
# repo — pytest las descubre automáticamente, no requieren import aquí.

import pytest


@pytest.fixture
async def pasajero_con_reserva(client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    """A diferencia de `pasajero_client`, esta fixture deja al `client` YA
    autenticado como el mismo pasajero dueño de la reserva creada — usarla
    sola (sin combinarla con `pasajero_client`, que crea un pasajero
    distinto) quando el test necesita ver su propia reserva."""
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada")
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    return {
        "usuario": usuario,
        "pasajero": pasajero,
        "vuelo": vuelo,
        "tarifa": tarifa,
        "reserva": reserva,
        "client": client,
    }


@pytest.fixture
async def pasajero_client(client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    client.pasajero = pasajero
    client.pasajero_usuario = usuario
    return client