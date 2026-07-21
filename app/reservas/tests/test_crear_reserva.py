from app.reservas.services.pago_stub_service import confirmar_pago_reserva


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

    reserva = await pb.get_record("reservas", reserva_id)
    assert reserva["estado"] == "pendiente_pago"
    assert reserva["canal"] == "autoservicio"
    assert reserva["fecha_expiracion_pago"]
    assert reserva["total_pagar"] == 250.0

    tarifa_actualizada = await pb.get_record("tarifas_vuelo", tarifa["id"])
    assert tarifa_actualizada["cupos_disponibles"] == 2  # RN-RES-001: cupo realmente decrementado

    await pb.delete_record("reserva_pasajeros", (await pb.list_records(
        "reserva_pasajeros", {"filter": f'reserva_id="{reserva_id}"'}
    ))["items"][0]["id"])
    # reserva_items (dual-write de crear_reserva_service) tiene una relación
    # requerida a reservas — hay que borrarlo antes o PocketBase rechaza el
    # delete de la reserva ("part of a required relation reference").
    for item in (await pb.list_records("reserva_items", {"filter": f'reserva_id="{reserva_id}"'}))["items"]:
        await pb.delete_record("reserva_items", item["id"])
    await pb.delete_record("reservas", reserva_id)


async def test_crear_reserva_sin_cupo_no_crea_nada(client, pb, pasajero_factory, vuelo_factory, tarifa_factory):
    usuario, _pasajero = await pasajero_factory()
    await _login(client, usuario)
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=0, precio_final=250.0)

    resp = await client.post(
        "/reservas", data={"tarifa_id": tarifa["id"], "precio_esperado": "250.0"}
    )
    assert resp.status_code == 409
    assert "cupo" in resp.text.lower()

    existentes = await pb.list_records("reservas", {"filter": f'tarifa_id="{tarifa["id"]}"'})
    assert existentes["totalItems"] == 0


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

    tarifa_sin_cambios = await pb.get_record("tarifas_vuelo", tarifa["id"])
    assert tarifa_sin_cambios["cupos_disponibles"] == 5  # nunca se llegó a invocar cupo_service


async def test_crear_reserva_sin_perfil_de_pasajero_rechaza(client, pb, usuario_factory, vuelo_factory, tarifa_factory):
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

async def test_confirmar_pago_reserva_pasa_a_confirmada(pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")

    actualizada = await confirmar_pago_reserva(reserva["id"])
    assert actualizada["estado"] == "confirmada"


# ── RF-RES-002 (CHK002, CHK019) ────────────────────────────────────────────

async def test_reserva_asistida_exige_rbac_y_registra_agente(
    admin_client, pb, pasajero_factory, vuelo_factory, tarifa_factory
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

    reserva = await pb.get_record("reservas", reserva_id)
    assert reserva["canal"] == "asistida"
    assert reserva["agente_id"] == admin_client.admin_usuario["id"]

    await pb.delete_record(
        "reserva_pasajeros",
        (await pb.list_records("reserva_pasajeros", {"filter": f'reserva_id="{reserva_id}"'}))["items"][0]["id"],
    )
    for item in (await pb.list_records("reserva_items", {"filter": f'reserva_id="{reserva_id}"'}))["items"]:
        await pb.delete_record("reserva_items", item["id"])
    await pb.delete_record("reservas", reserva_id)


async def test_reserva_asistida_sin_permiso_bloqueada(client, usuario_factory, rol_agente, vuelo_factory, tarifa_factory):
    # Sembrado: Agente SÍ tiene "crear" sobre reservas -> se usa un pasajero
    # (sin rol_id) para probar el bloqueo real por falta de RBAC.
    pasajero_sin_rol = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero_sin_rol["email"], "password": pasajero_sin_rol["_password"]})
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
