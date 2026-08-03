"""RF-VUE-011/012/013 (CU-O115/116/117) — mapa de asientos, selección con
regla de ventana de check-in por tarifa, y asignación automática."""

import datetime

import pytest

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.asientos_service import (
    AsientoNoDisponible,
    AsientoNoValido,
    SeleccionNoPermitidaAun,
    asignar_automaticamente,
    liberar_asiento,
    obtener_o_generar_mapa,
    validar_y_reservar_asiento,
)


@pytest.fixture
async def limpiar_asientos(pb):
    vuelos_creados: list[str] = []
    yield vuelos_creados
    for vuelo_id in vuelos_creados:
        asientos = await pb.list_records("asientos_vuelo", {"filter": f'vuelo_id="{vuelo_id}"', "perPage": 500})
        for a in asientos["items"]:
            await pb.delete_record("asientos_vuelo", a["id"])


# ── RF-VUE-011 (CU-O115) ────────────────────────────────────────────────

async def test_generar_mapa_crea_180_asientos_con_columnas_3_3(pb, vuelo_factory, limpiar_asientos):
    vuelo = await vuelo_factory()
    limpiar_asientos.append(vuelo["id"])

    asientos = await obtener_o_generar_mapa(vuelo["id"])
    assert len(asientos) == 180  # 30 filas x 6 columnas
    assert {a["columna"] for a in asientos} == {"A", "B", "C", "D", "E", "F"}
    assert all(a["tipo_asiento"] in ("ventana", "pasillo", "medio") for a in asientos)
    ventana = next(a for a in asientos if a["columna"] == "A")
    assert ventana["tipo_asiento"] == "ventana"
    pasillo = next(a for a in asientos if a["columna"] == "C")
    assert pasillo["tipo_asiento"] == "pasillo"


async def test_generar_mapa_es_idempotente(pb, vuelo_factory, limpiar_asientos):
    vuelo = await vuelo_factory()
    limpiar_asientos.append(vuelo["id"])

    primera = await obtener_o_generar_mapa(vuelo["id"])
    segunda = await obtener_o_generar_mapa(vuelo["id"])
    assert len(primera) == len(segunda) == 180
    assert {a["id"] for a in primera} == {a["id"] for a in segunda}


async def test_primeras_filas_son_premium_con_recargo(pb, vuelo_factory, limpiar_asientos):
    vuelo = await vuelo_factory()
    limpiar_asientos.append(vuelo["id"])

    asientos = await obtener_o_generar_mapa(vuelo["id"])
    fila_1 = [a for a in asientos if a["fila"] == 1]
    fila_30 = [a for a in asientos if a["fila"] == 30]
    assert all(a["es_premium"] and a["recargo"] > 0 for a in fila_1)
    assert all(not a["es_premium"] and a["recargo"] == 0 for a in fila_30)


# ── RF-VUE-012 (CU-O116) ────────────────────────────────────────────────

async def test_tarifa_standard_permite_asiento_estandar_de_inmediato(pb, vuelo_factory, limpiar_asientos):
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")
    limpiar_asientos.append(vuelo["id"])
    asientos = await obtener_o_generar_mapa(vuelo["id"])
    estandar = next(a for a in asientos if not a["es_premium"])
    nivel = {"seleccion_asiento_temprana": True}

    reservado = await validar_y_reservar_asiento(vuelo, nivel, estandar["id"])
    assert reservado["id"] == estandar["id"]
    fresco = await pb.get_record("asientos_vuelo", estandar["id"])
    assert fresco["disponible"] is False


async def test_tarifa_light_rechaza_asiento_estandar_antes_de_ventana(pb, vuelo_factory, limpiar_asientos):
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")  # muy lejos en el futuro
    limpiar_asientos.append(vuelo["id"])
    asientos = await obtener_o_generar_mapa(vuelo["id"])
    estandar = next(a for a in asientos if not a["es_premium"])
    nivel = {"seleccion_asiento_temprana": False}

    with pytest.raises(SeleccionNoPermitidaAun):
        await validar_y_reservar_asiento(vuelo, nivel, estandar["id"])
    fresco = await pb.get_record("asientos_vuelo", estandar["id"])
    assert fresco["disponible"] is True  # rechazado -> nunca se tocó


async def test_tarifa_light_permite_asiento_estandar_dentro_de_ventana(pb, vuelo_factory, limpiar_asientos):
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")
    limpiar_asientos.append(vuelo["id"])
    asientos = await obtener_o_generar_mapa(vuelo["id"])
    estandar = next(a for a in asientos if not a["es_premium"])
    nivel = {"seleccion_asiento_temprana": False}
    # "ahora" a 10 horas de la salida — dentro del default de 36h de ventana
    ahora = datetime.datetime(2027, 6, 14, 14, 0, tzinfo=datetime.timezone.utc)

    reservado = await validar_y_reservar_asiento(vuelo, nivel, estandar["id"], ahora=ahora)
    assert reservado["id"] == estandar["id"]


async def test_tarifa_light_permite_asiento_premium_de_inmediato(pb, vuelo_factory, limpiar_asientos):
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")
    limpiar_asientos.append(vuelo["id"])
    asientos = await obtener_o_generar_mapa(vuelo["id"])
    premium = next(a for a in asientos if a["es_premium"])
    nivel = {"seleccion_asiento_temprana": False}

    reservado = await validar_y_reservar_asiento(vuelo, nivel, premium["id"])
    assert reservado["es_premium"] is True
    assert reservado["recargo"] > 0


async def test_asiento_ya_ocupado_rechaza(pb, vuelo_factory, limpiar_asientos):
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")
    limpiar_asientos.append(vuelo["id"])
    asientos = await obtener_o_generar_mapa(vuelo["id"])
    premium = next(a for a in asientos if a["es_premium"])
    nivel = {"seleccion_asiento_temprana": True}

    await validar_y_reservar_asiento(vuelo, nivel, premium["id"])
    with pytest.raises(AsientoNoDisponible):
        await validar_y_reservar_asiento(vuelo, nivel, premium["id"])


async def test_asiento_de_otro_vuelo_rechaza(pb, vuelo_factory, limpiar_asientos):
    vuelo_a = await vuelo_factory(fecha_salida="2027-06-15")
    vuelo_b = await vuelo_factory(fecha_salida="2027-06-15")
    limpiar_asientos.append(vuelo_a["id"])
    limpiar_asientos.append(vuelo_b["id"])
    asientos_b = await obtener_o_generar_mapa(vuelo_b["id"])
    nivel = {"seleccion_asiento_temprana": True}

    with pytest.raises(AsientoNoValido):
        await validar_y_reservar_asiento(vuelo_a, nivel, asientos_b[0]["id"])


async def test_liberar_asiento_lo_vuelve_a_dejar_disponible(pb, vuelo_factory, limpiar_asientos):
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")
    limpiar_asientos.append(vuelo["id"])
    asientos = await obtener_o_generar_mapa(vuelo["id"])
    nivel = {"seleccion_asiento_temprana": True}
    reservado = await validar_y_reservar_asiento(vuelo, nivel, asientos[0]["id"])

    await liberar_asiento(reservado["id"])
    fresco = await pb.get_record("asientos_vuelo", reservado["id"])
    assert fresco["disponible"] is True


async def test_liberar_asiento_con_id_vacio_no_hace_nada(pb):
    await liberar_asiento(None)  # no debe lanzar


# ── RF-VUE-013 (CU-O117) ────────────────────────────────────────────────

async def test_asignacion_automatica_asigna_a_pasajero_confirmado_sin_asiento(
    pb, vuelo_factory, tarifa_factory, pasajero_factory, reserva_factory, limpiar_asientos
):
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")
    limpiar_asientos.append(vuelo["id"])
    nivel_light = await pb.get_first("niveles_tarifa", 'nombre="Light"')
    tarifa = await tarifa_factory(vuelo["id"], nivel_tarifa_id=nivel_light["id"])
    _usuario, pasajero = await pasajero_factory()
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada")
    reserva_pasajero = await ReservasRepository().agregar_pasajero(reserva["id"], pasajero["id"], "adulto")

    # "ahora" dentro de la ventana de check-in (default 36h antes de salida)
    ahora = datetime.datetime(2027, 6, 14, 14, 0, tzinfo=datetime.timezone.utc)
    asignados = await asignar_automaticamente(ahora=ahora)
    assert asignados >= 1

    fresco = await moc.obtener("reserva_pasajeros", reserva_pasajero["id"])
    assert fresco["asiento_id"]
    assert fresco["asiento_asignado_por"] == "sistema"

    asiento_asignado = await pb.get_record("asientos_vuelo", fresco["asiento_id"])
    assert asiento_asignado["disponible"] is False

    await moc.eliminar("reserva_pasajeros", reserva_pasajero["id"])


async def test_asignacion_automatica_ignora_pasajero_fuera_de_ventana(
    pb, vuelo_factory, tarifa_factory, pasajero_factory, reserva_factory, limpiar_asientos
):
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")
    limpiar_asientos.append(vuelo["id"])
    tarifa = await tarifa_factory(vuelo["id"])
    _usuario, pasajero = await pasajero_factory()
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada")
    reserva_pasajero = await ReservasRepository().agregar_pasajero(reserva["id"], pasajero["id"], "adulto")

    # "ahora" mucho antes de que abra la ventana de check-in
    ahora = datetime.datetime(2027, 1, 1, tzinfo=datetime.timezone.utc)
    await asignar_automaticamente(ahora=ahora)

    fresco = await moc.obtener("reserva_pasajeros", reserva_pasajero["id"])
    assert not fresco["asiento_id"]

    await moc.eliminar("reserva_pasajeros", reserva_pasajero["id"])
