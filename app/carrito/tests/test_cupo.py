"""Cupo real (2026-07-19) — Carrito no bloquea cupo al agregar (mismo
criterio de `carrito-spec.md`: "un carrito no es un PNR"), pero SÍ lo
verifica y reserva atómicamente al confirmar el checkout, todo o nada
(RN-CAR nuevo, generaliza RF-VUE-005 al resto de verticales vía
`app.shared.cupo_service`).

Hotel/Auto (RF-HOT-004/RF-AUT-004, gap real cerrado 2026-07-29): una
estadía/renta abarca N noches/días, cada una su propia fila de
disponibilidad — `app.shared.cupo_rango_service` reserva/libera TODAS a
la vez, con rollback manual si alguna falla a medio camino."""

from app.carrito.services.carrito_service import CupoInsuficiente, agregar_item, confirmar_checkout
from app.shared import minio_operational_client as moc


async def _crear_hotel_con_tarifa(pb, precio_final: float = 150.0, cupos_disponibles: int = 3) -> tuple[dict, dict]:
    hotel = await pb.create_record(
        "hoteles_catalogo",
        {
            "nombre": "Hotel Test Cupo Rango", "direccion": "1 Test St", "ciudad": "Paris", "pais": "France",
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        },
    )
    tarifa = await pb.create_record(
        "hoteles_tarifas",
        {
            "hotel_id": hotel["id"], "tipo_habitacion": "Standard", "precio_final": precio_final, "moneda": "USD",
            "reembolsable": True, "cupos_disponibles": cupos_disponibles, "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        },
    )
    return hotel, tarifa


async def _crear_disponibilidad(pb, hotel_id: str, tarifa_id: str, fecha: str, cupos_disponibles: int) -> dict:
    return await pb.create_record(
        "hoteles_disponibilidad",
        {
            "hotel_id": hotel_id, "hotel_tarifa_id": tarifa_id, "fecha": fecha,
            "cupos_disponibles": cupos_disponibles, "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        },
    )


async def test_checkout_actividad_decrementa_cupo_por_cantidad(pb, pasajero_factory, actividad_con_horario_factory):
    _usuario, pasajero = await pasajero_factory()
    _actividad, horario = await actividad_con_horario_factory(cupos_disponibles=5, precio=45.0)

    item = await agregar_item(
        pasajero["id"], "actividad", {"actividad_id": _actividad["id"], "actividad_horario_id": horario["id"]},
        precio_snapshot=45.0, cantidad=3,
    )
    carrito_id = item["carrito_id"]

    reserva = await confirmar_checkout(pasajero["id"])
    assert reserva["total_pagar"] == 135.0  # 45.0 * 3, no 45.0 (precio_snapshot es unitario)

    horario_actualizado = await moc.obtener("cupos_actividades_horarios", horario["id"])
    assert horario_actualizado["cupos_disponibles"] == 2  # 5 - 3

    reserva_items = await moc.listar_todos("reserva_items")
    reserva_items = [i for i in reserva_items if i.get("reserva_id") == reserva["id"]]
    assert reserva_items[0]["cantidad"] == 3
    assert reserva_items[0]["precio_final"] == 135.0

    for ri in reserva_items:
        await moc.eliminar("reserva_items", ri["id"])
    await moc.eliminar("reservas", reserva["id"])
    items_restantes = await moc.listar_todos("carrito_items")
    for ci in [i for i in items_restantes if i.get("carrito_id") == carrito_id]:
        await moc.eliminar("carrito_items", ci["id"])
    await moc.eliminar("carritos", carrito_id)


async def test_checkout_rechaza_si_cupo_insuficiente_y_no_crea_reserva(
    pb, pasajero_factory, actividad_con_horario_factory
):
    _usuario, pasajero = await pasajero_factory()
    _actividad, horario = await actividad_con_horario_factory(cupos_disponibles=2, precio=45.0)

    item = await agregar_item(
        pasajero["id"], "actividad", {"actividad_id": _actividad["id"], "actividad_horario_id": horario["id"]},
        precio_snapshot=45.0, cantidad=5,  # pide más de lo que hay
    )
    carrito_id = item["carrito_id"]

    try:
        await confirmar_checkout(pasajero["id"])
        raise AssertionError("debía lanzar CupoInsuficiente")
    except CupoInsuficiente as exc:
        assert item["id"] in exc.item_ids

    # cupo intacto — nada se decrementó
    horario_sin_cambios = await moc.obtener("cupos_actividades_horarios", horario["id"])
    assert horario_sin_cambios["cupos_disponibles"] == 2

    # el carrito sigue activo, no se creó ninguna reserva
    carrito = await moc.obtener("carritos", carrito_id)
    assert carrito["estado"] == "activo"
    reservas = await moc.listar_todos("reservas")
    reservas_creadas = [r for r in reservas if r.get("pasajero_titular_id") == pasajero["id"]]
    assert reservas_creadas == []

    await moc.eliminar("carrito_items", item["id"])
    await moc.eliminar("carritos", carrito_id)


async def test_checkout_todo_o_nada_libera_cupo_ya_reservado_si_otro_item_falla(
    pb, pasajero_factory, actividad_con_horario_factory
):
    """Dos ítems en el mismo carrito: el primero SÍ tiene cupo (se
    reservaría), el segundo NO — el checkout debe fallar completo y
    liberar el cupo del primero, no dejarlo descontado a medias."""
    _usuario, pasajero = await pasajero_factory()
    _act_ok, horario_ok = await actividad_con_horario_factory(cupos_disponibles=5, precio=20.0)
    _act_agotado, horario_agotado = await actividad_con_horario_factory(cupos_disponibles=1, precio=30.0)

    item_ok = await agregar_item(
        pasajero["id"], "actividad", {"actividad_id": _act_ok["id"], "actividad_horario_id": horario_ok["id"]},
        precio_snapshot=20.0, cantidad=1,
    )
    item_agotado = await agregar_item(
        pasajero["id"], "actividad", {"actividad_id": _act_agotado["id"], "actividad_horario_id": horario_agotado["id"]},
        precio_snapshot=30.0, cantidad=3,  # pide 3, solo hay 1
    )
    carrito_id = item_ok["carrito_id"]

    try:
        await confirmar_checkout(pasajero["id"])
        raise AssertionError("debía lanzar CupoInsuficiente")
    except CupoInsuficiente:
        pass

    # el cupo del ítem que SÍ alcanzaba queda intacto — no se dejó reservado
    horario_ok_actualizado = await moc.obtener("cupos_actividades_horarios", horario_ok["id"])
    assert horario_ok_actualizado["cupos_disponibles"] == 5

    await moc.eliminar("carrito_items", item_ok["id"])
    await moc.eliminar("carrito_items", item_agotado["id"])
    await moc.eliminar("carritos", carrito_id)


async def test_checkout_hotel_reserva_todas_las_noches_del_rango(pb, pasajero_factory):
    """3 noches, 2 habitaciones: cada noche se decrementa exactamente 2
    (unidades), NUNCA cantidad (6, que ya incluye el factor de noches) —
    ver la advertencia explícita en cupo_rango_service.py sobre este
    error de doble conteo."""
    _usuario, pasajero = await pasajero_factory()
    hotel, tarifa = await _crear_hotel_con_tarifa(pb, precio_final=150.0, cupos_disponibles=99)
    noche1 = await _crear_disponibilidad(pb, hotel["id"], tarifa["id"], "2027-08-01", 5)
    noche2 = await _crear_disponibilidad(pb, hotel["id"], tarifa["id"], "2027-08-02", 5)
    noche3 = await _crear_disponibilidad(pb, hotel["id"], tarifa["id"], "2027-08-03", 5)

    item = await agregar_item(
        pasajero["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": tarifa["id"]},
        precio_snapshot=150.0, cantidad=1,
        fecha_inicio="2027-08-01", fecha_fin="2027-08-04", unidades=2,
    )
    carrito_id = item["carrito_id"]
    assert item["cantidad"] == 6  # 2 habitaciones × 3 noches

    reserva = await confirmar_checkout(pasajero["id"])
    assert reserva["total_pagar"] == 900.0  # 150.0 * 6

    for noche in (noche1, noche2, noche3):
        fila = await moc.obtener("cupos_hoteles_disponibilidad", noche["id"])
        assert fila["cupos_disponibles"] == 3  # 5 - 2 (unidades, no cantidad)

    reserva_items = [i for i in await moc.listar_todos("reserva_items") if i.get("reserva_id") == reserva["id"]]
    assert reserva_items[0]["fecha_inicio"] == "2027-08-01"
    assert reserva_items[0]["fecha_fin"] == "2027-08-04"
    assert reserva_items[0]["unidades"] == 2

    for ri in reserva_items:
        await moc.eliminar("reserva_items", ri["id"])
    await moc.eliminar("reservas", reserva["id"])
    await moc.eliminar("carritos", carrito_id)
    for noche in (noche1, noche2, noche3):
        await pb.delete_record("hoteles_disponibilidad", noche["id"])
    await pb.delete_record("hoteles_tarifas", tarifa["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])


async def test_checkout_hotel_noche_intermedia_sin_cupo_bloquea_todo_el_item(pb, pasajero_factory):
    """La noche 2 de 3 no tiene cupo — el checkout falla y las noches 1 y 3
    (reservadas de paso antes de toparse con la 2) quedan intactas: rollback
    manual dentro de `verificar_y_reservar_cupo_rango`."""
    _usuario, pasajero = await pasajero_factory()
    hotel, tarifa = await _crear_hotel_con_tarifa(pb, precio_final=100.0)
    noche1 = await _crear_disponibilidad(pb, hotel["id"], tarifa["id"], "2027-09-01", 5)
    noche2 = await _crear_disponibilidad(pb, hotel["id"], tarifa["id"], "2027-09-02", 0)  # agotada
    noche3 = await _crear_disponibilidad(pb, hotel["id"], tarifa["id"], "2027-09-03", 5)

    item = await agregar_item(
        pasajero["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": tarifa["id"]},
        precio_snapshot=100.0, cantidad=1,
        fecha_inicio="2027-09-01", fecha_fin="2027-09-04", unidades=1,
    )
    carrito_id = item["carrito_id"]

    try:
        await confirmar_checkout(pasajero["id"])
        raise AssertionError("debía lanzar CupoInsuficiente")
    except CupoInsuficiente as exc:
        assert item["id"] in exc.item_ids

    fila1 = await moc.obtener("cupos_hoteles_disponibilidad", noche1["id"])
    assert fila1["cupos_disponibles"] == 5  # revertida, no quedó descontada a medias
    fila3 = await moc.obtener("cupos_hoteles_disponibilidad", noche3["id"])
    assert fila3 is None  # nunca se llegó a tocar (la 2 falló antes)

    carrito = await moc.obtener("carritos", carrito_id)
    assert carrito["estado"] == "activo"

    await moc.eliminar("carrito_items", item["id"])
    await moc.eliminar("carritos", carrito_id)
    for noche in (noche1, noche2, noche3):
        await pb.delete_record("hoteles_disponibilidad", noche["id"])
    await pb.delete_record("hoteles_tarifas", tarifa["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])


async def test_checkout_libera_noches_de_hotel_si_otro_item_del_carrito_falla(
    pb, pasajero_factory, actividad_con_horario_factory
):
    """Ítem de hotel (3 noches, todas con cupo) + ítem de actividad sin
    cupo suficiente en el mismo carrito: el checkout todo-o-nada debe
    liberar las 3 noches del hotel, no solo el ítem que falló."""
    _usuario, pasajero = await pasajero_factory()
    hotel, tarifa = await _crear_hotel_con_tarifa(pb, precio_final=100.0)
    noches = [
        await _crear_disponibilidad(pb, hotel["id"], tarifa["id"], f"2027-10-0{d}", 5) for d in (1, 2, 3)
    ]
    _act_agotada, horario_agotado = await actividad_con_horario_factory(cupos_disponibles=1, precio=30.0)

    item_hotel = await agregar_item(
        pasajero["id"], "hotel", {"hotel_id": hotel["id"], "hotel_tarifa_id": tarifa["id"]},
        precio_snapshot=100.0, cantidad=1,
        fecha_inicio="2027-10-01", fecha_fin="2027-10-04", unidades=1,
    )
    item_agotado = await agregar_item(
        pasajero["id"], "actividad", {"actividad_id": _act_agotada["id"], "actividad_horario_id": horario_agotado["id"]},
        precio_snapshot=30.0, cantidad=5,  # pide más de lo que hay
    )
    carrito_id = item_hotel["carrito_id"]

    try:
        await confirmar_checkout(pasajero["id"])
        raise AssertionError("debía lanzar CupoInsuficiente")
    except CupoInsuficiente:
        pass

    for noche in noches:
        fila = await moc.obtener("cupos_hoteles_disponibilidad", noche["id"])
        assert fila["cupos_disponibles"] == 5  # las 3 noches del hotel, liberadas

    await moc.eliminar("carrito_items", item_hotel["id"])
    await moc.eliminar("carrito_items", item_agotado["id"])
    await moc.eliminar("carritos", carrito_id)
    for noche in noches:
        await pb.delete_record("hoteles_disponibilidad", noche["id"])
    await pb.delete_record("hoteles_tarifas", tarifa["id"])
    await pb.delete_record("hoteles_catalogo", hotel["id"])
