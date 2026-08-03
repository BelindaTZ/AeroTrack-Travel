"""RF-OFE-003/RN-OFE-002/RN-OFE-003 (CU-O103) — aplicar cupón de
descuento sobre una reserva propia en `pendiente_pago`."""

from app.ofertas.services.ofertas_service import CuponInvalido, aplicar_cupon
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc


async def _crear_cupon(pb, **extra) -> dict:
    data = {
        "codigo": "TESTCUPON10", "tipo": "porcentaje", "valor": 10.0,
        "fecha_expiracion": "2030-01-01 00:00:00.000Z", "usos_actuales": 0, "activo": True,
    }
    data.update(extra)
    return await pb.create_record("cupones_descuento", data)


async def _usos_de_cupon(cupon_id: str) -> list[dict]:
    usos = await moc.listar_todos("cupones_uso")
    return [u for u in usos if u.get("cupon_id") == cupon_id]


async def test_aplicar_cupon_porcentaje(pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], total_pagar=200.0)
    cupon = await _crear_cupon(pb, valor=10.0)

    resultado = await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
    assert resultado["monto_descontado"] == 20.0
    assert resultado["nuevo_total"] == 180.0

    reserva_actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert reserva_actualizada["total_pagar"] == 180.0
    cupon_actualizado = await pb.get_record("cupones_descuento", cupon["id"])
    assert cupon_actualizado["usos_actuales"] == 1

    usos = await _usos_de_cupon(cupon["id"])
    assert len(usos) == 1
    for u in usos:
        await moc.eliminar("cupones_uso", u["id"])
    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_aplicar_cupon_monto_fijo(pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], total_pagar=100.0)
    cupon = await _crear_cupon(pb, tipo="monto_fijo", valor=15.0)

    resultado = await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
    assert resultado["monto_descontado"] == 15.0
    assert resultado["nuevo_total"] == 85.0

    for u in await _usos_de_cupon(cupon["id"]):
        await moc.eliminar("cupones_uso", u["id"])
    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_monto_fijo_nunca_deja_total_negativo(pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], total_pagar=10.0)
    cupon = await _crear_cupon(pb, tipo="monto_fijo", valor=50.0)

    resultado = await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
    assert resultado["monto_descontado"] == 10.0
    assert resultado["nuevo_total"] == 0.0

    for u in await _usos_de_cupon(cupon["id"]):
        await moc.eliminar("cupones_uso", u["id"])
    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_cupon_expirado_se_rechaza(pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])
    cupon = await _crear_cupon(pb, fecha_expiracion="2020-01-01 00:00:00.000Z")

    try:
        await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
        assert False, "debía rechazar el cupón expirado"
    except CuponInvalido as exc:
        assert "expirado" in str(exc).lower()

    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_cupon_sin_usos_disponibles_se_rechaza(pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])
    cupon = await _crear_cupon(pb, usos_maximos=1, usos_actuales=1)

    try:
        await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
        assert False, "debía rechazar el cupón sin usos"
    except CuponInvalido as exc:
        assert "usos" in str(exc).lower()

    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_cupon_no_se_aplica_dos_veces_a_la_misma_reserva(
    pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], total_pagar=200.0)
    cupon = await _crear_cupon(pb)

    await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
    try:
        await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
        assert False, "debía rechazar el doble canje (RN-OFE-002)"
    except CuponInvalido as exc:
        assert "ya se aplicó" in str(exc).lower()

    usos = await _usos_de_cupon(cupon["id"])
    assert len(usos) == 1
    for u in usos:
        await moc.eliminar("cupones_uso", u["id"])
    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_cupon_producto_no_aplicable_se_rechaza(pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])
    cupon = await _crear_cupon(pb, producto_aplicable="hotel")

    try:
        await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
        assert False, "debía rechazar el cupón de hotel sobre una reserva de vuelo"
    except CuponInvalido as exc:
        assert "hotel" in str(exc).lower()

    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_cupon_sobre_paquete_usa_default_global_no_acumulable(
    pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    """El default global sembrado es `false` (no acumulable) — ver
    `errores-conocidos.md`/CU-T44."""
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], es_paquete=True)
    cupon = await _crear_cupon(pb)  # acumulable_con_paquete no seteado -> usa default global

    try:
        await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
        assert False, "debía rechazar por el default global no-acumulable"
    except CuponInvalido as exc:
        assert "paquete" in str(exc).lower()

    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_excepcion_de_cupon_gana_sobre_default_global(
    pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    """RN-OFE-T03 — el default global es `false`, pero este cupón tiene
    su propia excepción explícita `true`, que debe ganar."""
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], es_paquete=True, total_pagar=100.0)
    cupon = await _crear_cupon(pb, acumulable_con_paquete=True)

    resultado = await aplicar_cupon(usuario, pasajero["id"], reserva["id"], cupon["codigo"])
    assert resultado["monto_descontado"] == 10.0

    for u in await _usos_de_cupon(cupon["id"]):
        await moc.eliminar("cupones_uso", u["id"])
    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_endpoint_aplicar_cupon_via_http(
    client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], total_pagar=200.0)
    cupon = await _crear_cupon(pb)

    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303

    resp = await client.post(
        "/checkout/aplicar-cupon", data={"reserva_id": reserva["id"], "codigo": cupon["codigo"]}
    )
    assert resp.status_code == 303
    assert "Cup" in resp.headers["location"]

    reserva_actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert reserva_actualizada["total_pagar"] == 180.0

    for u in await _usos_de_cupon(cupon["id"]):
        await moc.eliminar("cupones_uso", u["id"])
    await pb.delete_record("cupones_descuento", cupon["id"])
