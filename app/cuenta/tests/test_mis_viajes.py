"""RF-CTA-001 — agrupación real de reservas por próxima/activa/pasada,
vía `mis_viajes_agrupados` y el endpoint `GET /mis-viajes`. Usa el mismo
patrón E2E que `app/reservas/tests/test_multiproducto.py` (Carrito real,
sin insertar `reserva_items` a mano) para que el escenario de prueba
refleje el flujo de compra real."""

import datetime

from app.carrito.services.carrito_service import agregar_item, confirmar_checkout
from app.cuenta.services.cuenta_service import mis_viajes_agrupados


async def _crear_actividad_con_horario(pb, fecha: str) -> tuple[dict, dict]:
    actividad = await pb.create_record(
        "actividades_catalogo",
        {
            "nombre": "Tour de prueba Mis Viajes", "ciudad": "CiudadTestMV", "pais": "PaisTestMV",
            "precio_desde": 40.0, "moneda": "USD", "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        },
    )
    horario = await pb.create_record(
        "actividades_horarios",
        {
            "actividad_id": actividad["id"], "fecha": fecha, "hora": "10:00",
            "cupos_disponibles": 5, "precio": 40.0, "moneda": "USD",
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        },
    )
    return actividad, horario


async def _limpiar_reserva(pb, reserva_id: str) -> None:
    items = await pb.list_records("reserva_items", {"filter": f'reserva_id="{reserva_id}"'})
    for ri in items["items"]:
        await pb.delete_record("reserva_items", ri["id"])
    await pb.delete_record("reservas", reserva_id)


async def test_reserva_de_actividad_futura_cae_en_proximas(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    fecha_futura = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    actividad, horario = await _crear_actividad_con_horario(pb, fecha_futura)

    await agregar_item(
        pasajero["id"], "actividad",
        {"actividad_id": actividad["id"], "actividad_horario_id": horario["id"]}, precio_snapshot=40.0,
    )
    reserva = await confirmar_checkout(pasajero["id"])

    grupos = await mis_viajes_agrupados(pasajero["id"])
    assert reserva["id"] in [g.id for g in grupos["proximas"]]
    assert reserva["id"] not in [g.id for g in grupos["pasadas"]] + [g.id for g in grupos["activas"]]

    await _limpiar_reserva(pb, reserva["id"])
    await pb.delete_record("actividades_horarios", horario["id"])
    await pb.delete_record("actividades_catalogo", actividad["id"])


async def test_reserva_de_actividad_pasada_cae_en_pasadas(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    fecha_pasada = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    actividad, horario = await _crear_actividad_con_horario(pb, fecha_pasada)

    await agregar_item(
        pasajero["id"], "actividad",
        {"actividad_id": actividad["id"], "actividad_horario_id": horario["id"]}, precio_snapshot=40.0,
    )
    reserva = await confirmar_checkout(pasajero["id"])

    grupos = await mis_viajes_agrupados(pasajero["id"])
    assert reserva["id"] in [g.id for g in grupos["pasadas"]]

    await _limpiar_reserva(pb, reserva["id"])
    await pb.delete_record("actividades_horarios", horario["id"])
    await pb.delete_record("actividades_catalogo", actividad["id"])


async def test_reserva_de_actividad_hoy_cae_en_activas(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    hoy = datetime.date.today().isoformat()
    actividad, horario = await _crear_actividad_con_horario(pb, hoy)

    await agregar_item(
        pasajero["id"], "actividad",
        {"actividad_id": actividad["id"], "actividad_horario_id": horario["id"]}, precio_snapshot=40.0,
    )
    reserva = await confirmar_checkout(pasajero["id"])

    grupos = await mis_viajes_agrupados(pasajero["id"])
    assert reserva["id"] in [g.id for g in grupos["activas"]]

    await _limpiar_reserva(pb, reserva["id"])
    await pb.delete_record("actividades_horarios", horario["id"])
    await pb.delete_record("actividades_catalogo", actividad["id"])


async def test_reserva_de_auto_sin_fecha_cae_en_sin_fecha(client, pb, pasajero_factory):
    """Auto no captura fecha de recogida en Carrito todavía (gap real
    documentado) — no debe clasificarse como próxima/activa/pasada."""
    usuario, pasajero = await pasajero_factory()
    auto = await pb.create_record(
        "autos_catalogo",
        {
            "proveedor_agregador": "expedia", "marca": "", "modelo": "Auto Mis Viajes",
            "categoria": "SUV", "transmision": "Automatic", "ciudad_recogida": "Lima",
            "aeropuerto_codigo": "LIM", "precio_dia": 50.0, "moneda": "USD",
            "modalidad_pago_disponible": "pagar_al_recoger", "fuente_oferta_ref": "token-mv",
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        },
    )
    await agregar_item(pasajero["id"], "auto", {"auto_id": auto["id"]}, precio_snapshot=50.0)
    reserva = await confirmar_checkout(pasajero["id"])

    grupos = await mis_viajes_agrupados(pasajero["id"])
    assert reserva["id"] in [g.id for g in grupos["sin_fecha"]]

    await _limpiar_reserva(pb, reserva["id"])
    await pb.delete_record("autos_catalogo", auto["id"])


async def test_endpoint_mis_viajes_requiere_sesion(client):
    resp = await client.get("/mis-viajes")
    assert resp.status_code in (303, 307)


async def test_endpoint_mis_viajes_lista_seccion_proxima(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    fecha_futura = (datetime.date.today() + datetime.timedelta(days=15)).isoformat()
    actividad, horario = await _crear_actividad_con_horario(pb, fecha_futura)
    await agregar_item(
        pasajero["id"], "actividad",
        {"actividad_id": actividad["id"], "actividad_horario_id": horario["id"]}, precio_snapshot=40.0,
    )
    reserva = await confirmar_checkout(pasajero["id"])

    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303
    resp = await client.get("/mis-viajes")
    assert resp.status_code == 200
    assert reserva["codigo_reserva"] in resp.text
    assert "Próximas" in resp.text

    await _limpiar_reserva(pb, reserva["id"])
    await pb.delete_record("actividades_horarios", horario["id"])
    await pb.delete_record("actividades_catalogo", actividad["id"])
