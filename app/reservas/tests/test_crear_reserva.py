from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.services.pago_stub_service import confirmar_pago_reserva
from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import get_pocketbase_client
from app.vuelos.services.asientos_service import obtener_o_generar_mapa


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    return resp


# ── RF-RES-001 / RN-RES-001 (CHK001, CHK010, CHK017) ──────────────────────

async def test_crear_reserva_con_cupo_crea_pendiente_pago(client, pb, pasajero_factory, vuelo_factory, tarifa_factory):
    usuario, _pasajero = await pasajero_factory()
    await _login(client, usuario)
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=3, precio_final=250.0)

    resp = await client.post(
        "/reservas", data={"tarifa_id": tarifa["id"], "precio_esperado": "250.0"}
    )
    assert resp.status_code == 303
    reserva_id = resp.headers["location"].rsplit("/", 1)[-1]

    repo = ReservasRepository()
    reserva = await repo.obtener_reserva(reserva_id)
    assert reserva["estado"] == "pendiente_pago"
    assert reserva["canal"] == "autoservicio"
    assert reserva["fecha_expiracion_pago"]
    assert reserva["total_pagar"] == 250.0

    tarifa_actualizada = await moc.obtener("cupos_tarifas_vuelo", tarifa["id"])
    assert tarifa_actualizada["cupos_disponibles"] == 2  # RN-RES-001: cupo realmente decrementado

    pasajeros_reserva = await repo.pasajeros_de_reserva(reserva_id)
    await moc.eliminar("reserva_pasajeros", pasajeros_reserva[0]["id"])
    # reserva_items (dual-write de crear_reserva_service) — se borra antes
    # que la reserva por prolijidad (ya no hay relation field que lo exija).
    for item in await repo.items_de_reserva(reserva_id):
        await moc.eliminar("reserva_items", item["id"])
    await moc.eliminar("reservas", reserva_id)


async def test_crear_reserva_sin_cupo_no_crea_nada(client, pasajero_factory, vuelo_factory, tarifa_factory):
    usuario, _pasajero = await pasajero_factory()
    await _login(client, usuario)
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=0, precio_final=250.0)

    resp = await client.post(
        "/reservas", data={"tarifa_id": tarifa["id"], "precio_esperado": "250.0"}
    )
    assert resp.status_code == 409
    assert "cupo" in resp.text.lower()

    reservas = await moc.listar_todos("reservas")
    existentes = [r for r in reservas if r.get("tarifa_id") == tarifa["id"]]
    assert existentes == []


# ── RNF-RES-001 (CHK016) ───────────────────────────────────────────────────

async def test_crear_reserva_con_precio_desactualizado_rechaza_sin_tocar_cupo(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory
):
    usuario, _pasajero = await pasajero_factory()
    await _login(client, usuario)
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=5, precio_final=250.0)

    resp = await client.post(
        "/reservas", data={"tarifa_id": tarifa["id"], "precio_esperado": "199.0"}
    )
    assert resp.status_code == 409
    assert "precio" in resp.text.lower()

    tarifa_sin_cambios = await moc.obtener("cupos_tarifas_vuelo", tarifa["id"])
    assert tarifa_sin_cambios is None  # nunca se llegó a invocar cupo_service, ni se sembró en MinIO


async def test_crear_reserva_sin_perfil_de_pasajero_rechaza(client, usuario_factory, vuelo_factory, tarifa_factory):
    # tipo_actor="pasajero" pero sin registro en `pasajeros` (no pasó por el
    # flujo de registro real) -> PasajeroNoEncontrado
    usuario = await usuario_factory(tipo_actor="pasajero")
    await _login(client, usuario)
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=5, precio_final=250.0)

    resp = await client.post(
        "/reservas", data={"tarifa_id": tarifa["id"], "precio_esperado": "250.0"}
    )
    assert resp.status_code == 400


# ── pago_stub_service (base para RN-RES-006 y RN-RES-005) ────────────────

async def test_confirmar_pago_reserva_pasa_a_confirmada(pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")

    actualizada = await confirmar_pago_reserva(reserva["id"])
    assert actualizada["estado"] == "confirmada"


# ── RF-RES-002 (CHK002, CHK019) ────────────────────────────────────────────

async def test_reserva_asistida_exige_rbac_y_registra_agente(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory
):
    usuario_pax, _pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=3, precio_final=300.0)

    resp = await admin_client.post(
        "/backoffice/reservas",
        data={"email_pasajero": usuario_pax["email"], "tarifa_id": tarifa["id"], "precio_esperado": "300.0"},
    )
    assert resp.status_code == 303
    reserva_id = resp.headers["location"].rsplit("/", 1)[-1]

    repo = ReservasRepository()
    reserva = await repo.obtener_reserva(reserva_id)
    assert reserva["canal"] == "asistida"
    assert reserva["agente_id"] == admin_client.admin_usuario["id"]

    pasajeros_reserva = await repo.pasajeros_de_reserva(reserva_id)
    await moc.eliminar("reserva_pasajeros", pasajeros_reserva[0]["id"])
    for item in await repo.items_de_reserva(reserva_id):
        await moc.eliminar("reserva_items", item["id"])
    await moc.eliminar("reservas", reserva_id)


async def test_reserva_asistida_sin_permiso_bloqueada(client, usuario_factory, rol_agente, vuelo_factory, tarifa_factory):
    # Sembrado: Agente SÍ tiene "crear" sobre reservas; el rol "Pasajero" solo
    # tiene "ver" -> se usa un pasajero para probar el bloqueo real por RBAC.
    pasajero = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])

    resp = await client.post(
        "/backoffice/reservas",
        data={"email_pasajero": "quien-sea@aerotrack.test", "tarifa_id": tarifa["id"], "precio_esperado": "199.0"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 403


async def test_reserva_asistida_pasajero_inexistente_rechaza(admin_client, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])

    resp = await admin_client.post(
        "/backoffice/reservas",
        data={
            "email_pasajero": "no-existe-nunca@aerotrack.test",
            "tarifa_id": tarifa["id"],
            "precio_esperado": str(tarifa["precio_final"]),
        },
    )
    assert resp.status_code == 404


# ── RF-VUE-012 (CU-O116, selección de asiento) ────────────────────────────

async def _limpiar_reserva(reserva_id):
    repo = ReservasRepository()
    for r in await repo.pasajeros_de_reserva(reserva_id):
        await moc.eliminar("reserva_pasajeros", r["id"])
    for r in await repo.extras_de_reserva(reserva_id):
        await moc.eliminar("reserva_extras", r["id"])
    for r in await repo.items_de_reserva(reserva_id):
        await moc.eliminar("reserva_items", r["id"])
    await moc.eliminar("reservas", reserva_id)


async def test_crear_reserva_con_asiento_premium_cobra_recargo(
    pb, client, pasajero_factory, vuelo_factory, tarifa_factory
):
    usuario, _pasajero = await pasajero_factory()
    await _login(client, usuario)
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")
    nivel_standard = await pb.get_first("niveles_tarifa", 'nombre="Standard"')
    tarifa = await tarifa_factory(vuelo["id"], precio_final=250.0, nivel_tarifa_id=nivel_standard["id"])
    asientos = await obtener_o_generar_mapa(vuelo["id"])
    premium = next(a for a in asientos if a["es_premium"])

    resp = await client.post(
        "/reservas",
        data={"tarifa_id": tarifa["id"], "precio_esperado": "250.0", "asiento_id": premium["id"]},
    )
    assert resp.status_code == 303
    reserva_id = resp.headers["location"].rsplit("/", 1)[-1]

    repo = ReservasRepository()
    reserva = await repo.obtener_reserva(reserva_id)
    assert reserva["total_pagar"] == round(250.0 + premium["recargo"], 2)

    pasajero_reserva = (await repo.pasajeros_de_reserva(reserva_id))[0]
    assert pasajero_reserva["asiento_id"] == premium["id"]
    assert pasajero_reserva["asiento_asignado_por"] == "pasajero"

    asiento_fresco = await pb.get_record("asientos_vuelo", premium["id"])
    assert asiento_fresco["disponible"] is False

    await _limpiar_reserva(reserva_id)
    for a in asientos:
        await pb.delete_record("asientos_vuelo", a["id"])


async def test_crear_reserva_con_asiento_ya_tomado_libera_cupo_y_no_crea_nada(
    pb, client, pasajero_factory, vuelo_factory, tarifa_factory
):
    usuario, _pasajero = await pasajero_factory()
    await _login(client, usuario)
    vuelo = await vuelo_factory(fecha_salida="2027-06-15")
    nivel_standard = await pb.get_first("niveles_tarifa", 'nombre="Standard"')
    tarifa = await tarifa_factory(
        vuelo["id"], cupos_disponibles=3, precio_final=250.0, nivel_tarifa_id=nivel_standard["id"]
    )
    asientos = await obtener_o_generar_mapa(vuelo["id"])
    estandar = next(a for a in asientos if not a["es_premium"])
    await pb.update_record("asientos_vuelo", estandar["id"], {"disponible": False})  # ya tomado

    resp = await client.post(
        "/reservas",
        data={"tarifa_id": tarifa["id"], "precio_esperado": "250.0", "asiento_id": estandar["id"]},
    )
    assert resp.status_code == 409
    assert "asiento" in resp.text.lower()

    tarifa_sin_cambios = await moc.obtener("cupos_tarifas_vuelo", tarifa["id"])
    assert tarifa_sin_cambios["cupos_disponibles"] == 3  # el cupo reservado se liberó al fallar el asiento

    reservas = await moc.listar_todos("reservas")
    existentes = [r for r in reservas if r.get("tarifa_id") == tarifa["id"]]
    assert existentes == []

    for a in asientos:
        await pb.delete_record("asientos_vuelo", a["id"])


# ── ampliación de sesión 2026-08-01 — precio de extras editable desde
# Configuración del sistema (reservas.precio_extra_equipaje/_seguro) ──────

async def test_checkout_usa_precio_de_extra_configurado(client, pasajero_factory, vuelo_factory, tarifa_factory):
    pb_client = get_pocketbase_client()
    config = await pb_client.get_first("configuracion_sistema", 'clave="reservas.precio_extra_equipaje"')
    original = config["valor"]
    await pb_client.update_record("configuracion_sistema", config["id"], {"valor": "99.5"})
    try:
        usuario, _pasajero = await pasajero_factory()
        await _login(client, usuario)
        vuelo = await vuelo_factory()
        tarifa = await tarifa_factory(vuelo["id"])

        resp = await client.get("/reservas/nueva", params={"tarifa_id": tarifa["id"]})
        assert resp.status_code == 200
        assert "99.50" in resp.text
    finally:
        await pb_client.update_record("configuracion_sistema", config["id"], {"valor": original})
