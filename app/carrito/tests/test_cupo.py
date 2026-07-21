"""Cupo real (2026-07-19) — Carrito no bloquea cupo al agregar (mismo
criterio de `carrito-spec.md`: "un carrito no es un PNR"), pero SÍ lo
verifica y reserva atómicamente al confirmar el checkout, todo o nada
(RN-CAR nuevo, generaliza RF-VUE-005 al resto de verticales vía
`app.shared.cupo_service`)."""

from app.carrito.services.carrito_service import CupoInsuficiente, agregar_item, confirmar_checkout


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

    horario_actualizado = await pb.get_record("actividades_horarios", horario["id"])
    assert horario_actualizado["cupos_disponibles"] == 2  # 5 - 3

    reserva_items = await pb.list_records("reserva_items", {"filter": f'reserva_id="{reserva["id"]}"'})
    assert reserva_items["items"][0]["cantidad"] == 3
    assert reserva_items["items"][0]["precio_final"] == 135.0

    for ri in reserva_items["items"]:
        await pb.delete_record("reserva_items", ri["id"])
    await pb.delete_record("reservas", reserva["id"])
    items_restantes = await pb.list_records("carrito_items", {"filter": f'carrito_id="{carrito_id}"'})
    for ci in items_restantes["items"]:
        await pb.delete_record("carrito_items", ci["id"])
    await pb.delete_record("carritos", carrito_id)


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
    horario_sin_cambios = await pb.get_record("actividades_horarios", horario["id"])
    assert horario_sin_cambios["cupos_disponibles"] == 2

    # el carrito sigue activo, no se creó ninguna reserva
    carrito = await pb.get_record("carritos", carrito_id)
    assert carrito["estado"] == "activo"
    reservas_creadas = await pb.list_records("reservas", {"filter": f'pasajero_titular_id="{pasajero["id"]}"'})
    assert reservas_creadas["totalItems"] == 0

    await pb.delete_record("carrito_items", item["id"])
    await pb.delete_record("carritos", carrito_id)


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
    horario_ok_actualizado = await pb.get_record("actividades_horarios", horario_ok["id"])
    assert horario_ok_actualizado["cupos_disponibles"] == 5

    await pb.delete_record("carrito_items", item_ok["id"])
    await pb.delete_record("carrito_items", item_agotado["id"])
    await pb.delete_record("carritos", carrito_id)
