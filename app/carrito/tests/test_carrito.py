"""RF-CAR-001,002,003 (CU-O93,O94,O95)."""

from app.carrito.repositories.carrito_repo import CarritoRepository
from app.carrito.services.carrito_service import agregar_item, eliminar_item, ver_carrito
from app.shared import minio_operational_client as moc


async def test_agregar_item_crea_carrito_activo_si_no_existe(pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=250.0)

    item = await agregar_item(
        pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa["id"]}, 250.0
    )

    carrito = await CarritoRepository().carrito_de_trabajo(pasajero["id"])
    assert carrito is not None
    assert item["carrito_id"] == carrito["id"]
    assert item["precio_snapshot"] == 250.0

    await moc.eliminar("carrito_items", item["id"])
    await moc.eliminar("carritos", carrito["id"])


async def test_agregar_dos_items_reutiliza_el_mismo_carrito(pasajero_factory, vuelo_factory, tarifa_factory):
    """RN-CAR-002 — un pasajero tiene a lo sumo un carrito activo."""
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa_a = await tarifa_factory(vuelo["id"], precio_final=100.0)
    tarifa_b = await tarifa_factory(vuelo["id"], precio_final=150.0)

    item_a = await agregar_item(pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa_a["id"]}, 100.0)
    item_b = await agregar_item(pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa_b["id"]}, 150.0)

    assert item_a["carrito_id"] == item_b["carrito_id"]

    carritos = await moc.listar_todos("carritos")
    activos = [c for c in carritos if c.get("pasajero_id") == pasajero["id"] and c.get("estado") == "activo"]
    assert len(activos) == 1  # nunca se crea un segundo carrito en paralelo

    await moc.eliminar("carrito_items", item_a["id"])
    await moc.eliminar("carrito_items", item_b["id"])
    await moc.eliminar("carritos", item_a["carrito_id"])


async def test_ver_carrito_suma_precios_snapshot(pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa_a = await tarifa_factory(vuelo["id"], precio_final=100.0)
    tarifa_b = await tarifa_factory(vuelo["id"], precio_final=150.0)

    await agregar_item(pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa_a["id"]}, 100.0)
    await agregar_item(pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa_b["id"]}, 150.0)

    resultado = await ver_carrito(pasajero["id"])
    assert len(resultado["items"]) == 2
    assert resultado["total"] == 250.0

    for item in resultado["items"]:
        await moc.eliminar("carrito_items", item["id"])
    await moc.eliminar("carritos", resultado["carrito"]["id"])


async def test_ver_carrito_sin_carrito_activo_devuelve_vacio(pasajero_factory):
    _usuario, pasajero = await pasajero_factory()
    resultado = await ver_carrito(pasajero["id"])
    assert resultado == {"carrito": None, "items": [], "total": 0.0}


async def test_eliminar_item_no_afecta_los_demas(pasajero_factory, vuelo_factory, tarifa_factory):
    _usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa_a = await tarifa_factory(vuelo["id"], precio_final=100.0)
    tarifa_b = await tarifa_factory(vuelo["id"], precio_final=150.0)

    item_a = await agregar_item(pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa_a["id"]}, 100.0)
    item_b = await agregar_item(pasajero["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa_b["id"]}, 150.0)

    await eliminar_item(pasajero["id"], item_a["id"])

    resultado = await ver_carrito(pasajero["id"])
    assert len(resultado["items"]) == 1
    assert resultado["items"][0]["id"] == item_b["id"]

    await moc.eliminar("carrito_items", item_b["id"])
    await moc.eliminar("carritos", resultado["carrito"]["id"])


async def test_eliminar_item_de_otro_pasajero_rechaza(pasajero_factory, vuelo_factory, tarifa_factory):
    from app.carrito.services.carrito_service import SinPermiso

    _usuario_a, pasajero_a = await pasajero_factory()
    _usuario_b, pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], precio_final=100.0)

    item = await agregar_item(pasajero_a["id"], "vuelo", {"vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa["id"]}, 100.0)

    try:
        await eliminar_item(pasajero_b["id"], item["id"])
        raise AssertionError("debía lanzar SinPermiso")
    except SinPermiso:
        pass

    carrito = await CarritoRepository().carrito_de_trabajo(pasajero_a["id"])
    await moc.eliminar("carrito_items", item["id"])
    await moc.eliminar("carritos", carrito["id"])
