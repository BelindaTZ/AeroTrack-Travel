"""RF-PAS-001 / CU-O14 — Consultar historial de reservas propio."""

import pytest


@pytest.mark.asyncio
async def test_historial_muestra_solo_mis_reservas(pasajero_con_reserva):
    resp = await pasajero_con_reserva["client"].get("/mis-reservas")
    assert resp.status_code == 200
    body = resp.text
    assert pasajero_con_reserva["reserva"]["codigo_reserva"] in body


@pytest.mark.asyncio
async def test_historial_sin_perfil_pasajero_retorna_vacio(client, usuario_factory):
    usuario = await usuario_factory(tipo_actor="pasajero")
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303
    resp = await client.get("/mis-reservas")
    assert resp.status_code == 200
    assert "No tienes reservas" in resp.text


@pytest.mark.asyncio
async def test_historial_sin_sesion_redirige(client):
    resp = await client.get("/mis-reservas")
    assert resp.status_code == 303


@pytest.mark.asyncio
async def test_historial_filtros_instantaneos(pasajero_con_reserva):
    client = pasajero_con_reserva["client"]
    resp = await client.get("/mis-reservas?estado=confirmada")
    assert resp.status_code == 200
    assert pasajero_con_reserva["reserva"]["codigo_reserva"] in resp.text

    resp = await client.get("/mis-reservas?estado=cancelada")
    assert resp.status_code == 200
    assert pasajero_con_reserva["reserva"]["codigo_reserva"] not in resp.text


@pytest.mark.asyncio
async def test_historial_filtro_rango_fechas(pasajero_con_reserva):
    """RNF-PAS-001 — el rango de fecha filtra por la fecha del VUELO
    (`vuelos_catalogo.fecha_salida`), no por un campo inexistente en
    `reservas`; regresión del bug donde el filtro apuntaba a un campo que
    no existe en la colección `reservas`."""
    client = pasajero_con_reserva["client"]
    # PocketBase normaliza `date` a timestamp completo ("...00:00:00.000Z");
    # un <input type="date"> real siempre manda "YYYY-MM-DD" puro.
    fecha_vuelo = pasajero_con_reserva["vuelo"]["fecha_salida"][:10]

    resp = await client.get(f"/mis-reservas?fecha_desde={fecha_vuelo}&fecha_hasta={fecha_vuelo}")
    assert resp.status_code == 200
    assert pasajero_con_reserva["reserva"]["codigo_reserva"] in resp.text

    resp = await client.get("/mis-reservas?fecha_desde=2099-01-01")
    assert resp.status_code == 200
    assert pasajero_con_reserva["reserva"]["codigo_reserva"] not in resp.text