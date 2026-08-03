"""IS-10 (auditoría de informes simples, sesión 2026-08-01) — listado de
`reserva_items` por tipo de producto, filtro de período, estado de la
reserva padre y exportar CSV. La descripción del ítem reutiliza
`describir_item` (compartida con Carrito/Mis reservas), no se reimplementa
acá."""

from app.reservas.repositories.reservas_repo import ReservasRepository


async def test_filtro_por_tipo_producto(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])
    # `reserva_factory` ya crea el item tipo=vuelo correspondiente.

    resp = await admin_client.get("/backoffice/reservas/items?tipo_producto=vuelo")
    assert resp.status_code == 200
    assert reserva["codigo_reserva"] in resp.text
    assert f"Vuelo {vuelo['numero_vuelo']}" in resp.text

    resp_otro_tipo = await admin_client.get("/backoffice/reservas/items?tipo_producto=hotel")
    assert reserva["codigo_reserva"] not in resp_otro_tipo.text


async def test_filtro_por_estado_de_reserva_padre(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    confirmada = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada")
    pendiente = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago")

    resp = await admin_client.get("/backoffice/reservas/items?estado=confirmada")
    assert resp.status_code == 200
    assert confirmada["codigo_reserva"] in resp.text
    assert pendiente["codigo_reserva"] not in resp.text


async def test_filtro_por_periodo(admin_client, pasajero_factory, vuelo_factory, tarifa_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    repo = ReservasRepository()
    reserva = await repo.crear_reserva(
        {
            "codigo_reserva": "PNRVIEJOTEST",
            "pasajero_titular_id": pasajero["id"], "vuelo_id": vuelo["id"], "tarifa_id": tarifa["id"],
            "canal": "autoservicio", "estado": "confirmada", "total_pagar": 199.0,
            "fecha_reserva": "2020-01-01 00:00:00.000Z", "fecha_expiracion_pago": "2020-01-01 00:15:00.000Z",
        }
    )
    item = await repo.crear_item(
        {
            "reserva_id": reserva["id"], "tipo_producto": "vuelo", "vuelo_id": vuelo["id"],
            "tarifa_vuelo_id": tarifa["id"], "precio_final": 199.0, "estado_item": "pendiente",
        }
    )
    # el `created` del item se genera automáticamente ("ahora") por
    # `_crear_registro` — se fuerza a una fecha vieja para probar el filtro.
    from app.shared import minio_operational_client as moc
    await moc.actualizar_con_reintento(
        "reserva_items", item["id"], lambda actual: {**actual, "created": "2020-01-01 00:00:00.000Z"}
    )

    resp = await admin_client.get("/backoffice/reservas/items?desde=2025-01-01")
    assert resp.status_code == 200
    assert "PNRVIEJOTEST" not in resp.text

    resp_incluye = await admin_client.get("/backoffice/reservas/items?hasta=2020-06-01")
    assert "PNRVIEJOTEST" in resp_incluye.text


async def test_paginacion(admin_client):
    resp = await admin_client.get("/backoffice/reservas/items?page=1")
    assert resp.status_code == 200

    resp = await admin_client.get("/backoffice/reservas/items?page=999")
    assert resp.status_code == 200


async def test_exportar_csv(admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])

    resp = await admin_client.get("/backoffice/reservas/items/exportar?tipo_producto=vuelo")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert resp.text.splitlines()[0] == (
        "tipo_producto,codigo_reserva,descripcion,precio_final,fecha,estado_reserva"
    )
    assert reserva["codigo_reserva"] in resp.text
