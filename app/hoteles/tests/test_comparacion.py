"""CU-T09 (RF-HOT-T01) — comparar hasta 5 propiedades de hotel lado a lado."""

import pytest

from app.hoteles.services.comparacion_service import DemasiadosHoteles, comparar_hoteles


async def test_compara_precio_estrellas_y_cancelacion(hotel_factory, tarifa_hotel_factory):
    hotel_a = await hotel_factory(nombre="Hotel A", estrellas=5, calificacion_promedio=4.8)
    hotel_b = await hotel_factory(nombre="Hotel B", estrellas=3, calificacion_promedio=3.9)
    await tarifa_hotel_factory(hotel_a["id"], precio_final=200.0, reembolsable=True, cancelacion_hasta="2027-06-01 00:00:00.000Z")
    await tarifa_hotel_factory(hotel_a["id"], precio_final=350.0, reembolsable=False)  # más cara, no debe ganar
    await tarifa_hotel_factory(hotel_b["id"], precio_final=90.0, reembolsable=False)

    filas = await comparar_hoteles([hotel_a["id"], hotel_b["id"]])
    assert len(filas) == 2

    fila_a = next(f for f in filas if f["id"] == hotel_a["id"])
    assert fila_a["precio_desde"] == 200.0  # la más económica, no cualquiera
    assert fila_a["reembolsable"] is True
    assert fila_a["estrellas"] == 5

    fila_b = next(f for f in filas if f["id"] == hotel_b["id"])
    assert fila_b["precio_desde"] == 90.0
    assert fila_b["reembolsable"] is False


async def test_rechaza_mas_de_cinco_hoteles(hotel_factory):
    hoteles = [await hotel_factory(nombre=f"Hotel {i}") for i in range(6)]
    with pytest.raises(DemasiadosHoteles):
        await comparar_hoteles([h["id"] for h in hoteles])


async def test_seis_ids_con_uno_repetido_no_cuenta_doble(hotel_factory):
    """RN-HOT-T01: el máximo es de propiedades ÚNICAS — repetir un id en la
    URL no debe contar como un sexto hotel distinto."""
    hoteles = [await hotel_factory(nombre=f"Hotel {i}") for i in range(5)]
    ids = [h["id"] for h in hoteles] + [hoteles[0]["id"]]  # 6 ids, 5 únicos
    filas = await comparar_hoteles(ids)
    assert len(filas) == 5


async def test_id_inexistente_se_omite_sin_romper(hotel_factory):
    hotel = await hotel_factory()
    filas = await comparar_hoteles([hotel["id"], "id-que-no-existe"])
    assert len(filas) == 1


async def test_hotel_sin_tarifas_muestra_sin_precio(hotel_factory):
    hotel = await hotel_factory()
    filas = await comparar_hoteles([hotel["id"]])
    assert filas[0]["precio_desde"] is None


async def test_endpoint_comparar_muestra_dos_hoteles(client, hotel_factory, tarifa_hotel_factory):
    hotel_a = await hotel_factory(nombre="Hotel Comparado Uno")
    hotel_b = await hotel_factory(nombre="Hotel Comparado Dos")
    await tarifa_hotel_factory(hotel_a["id"], precio_final=150.0)
    await tarifa_hotel_factory(hotel_b["id"], precio_final=99.0)

    resp = await client.get(f"/hoteles/comparar?ids={hotel_a['id']},{hotel_b['id']}")
    assert resp.status_code == 200
    assert "Hotel Comparado Uno" in resp.text
    assert "Hotel Comparado Dos" in resp.text
    assert "$150" in resp.text
    assert "$99" in resp.text


async def test_endpoint_comparar_mas_de_cinco_rechaza_explicito(client, hotel_factory):
    hoteles = [await hotel_factory(nombre=f"Hotel Rechazo {i}") for i in range(6)]
    ids = ",".join(h["id"] for h in hoteles)

    resp = await client.get(f"/hoteles/comparar?ids={ids}")
    assert resp.status_code == 400
    assert "5" in resp.text  # mensaje explícito, no un reemplazo silencioso


async def test_endpoint_comparar_no_requiere_sesion(client, hotel_factory, tarifa_hotel_factory):
    """RF-HOT-T01: de cara al pasajero, sin RBAC interno — un invitado
    también puede comparar."""
    hotel_a = await hotel_factory()
    hotel_b = await hotel_factory()
    resp = await client.get(f"/hoteles/comparar?ids={hotel_a['id']},{hotel_b['id']}")
    assert resp.status_code == 200
