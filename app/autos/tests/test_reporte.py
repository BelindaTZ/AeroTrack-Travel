"""CU-T11 (Autos Táctico) — reporte de reservas por proveedor/categoría."""

import datetime

import pytest

from app.autos.services.reporte_service import reporte_por_proveedor_categoria
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc


@pytest.fixture
async def reserva_item_auto_factory(pasajero_factory):
    """CU-T11 lee `reserva_items`, pero `reserva_id` es requerido ahí — se
    crea una `reservas` mínima (sin vuelo_id/tarifa_id, opcionales desde el
    rediseño v3) solo para satisfacer esa relación, no es el foco del test."""
    items_creados: list[str] = []
    reservas_creadas: list[str] = []

    async def _crear(auto_id: str, estado_item: str = "confirmado", precio_final: float = 63.0) -> dict:
        _usuario, pasajero = await pasajero_factory()
        ahora = "2027-01-01 00:00:00.000Z"
        repo = ReservasRepository()
        reserva = await repo.crear_reserva(
            {
                "codigo_reserva": f"AUT{len(reservas_creadas)}{auto_id[:4]}",
                "pasajero_titular_id": pasajero["id"],
                "canal": "autoservicio", "estado": "confirmada", "fecha_reserva": ahora,
            },
        )
        reservas_creadas.append(reserva["id"])

        item = await repo.crear_item(
            {
                "reserva_id": reserva["id"], "tipo_producto": "auto", "auto_id": auto_id,
                "estado_item": estado_item, "precio_final": precio_final, "cantidad": 1,
            },
        )
        items_creados.append(item["id"])
        return item

    yield _crear

    for item_id in items_creados:
        try:
            await moc.eliminar("reserva_items", item_id)
        except Exception:
            pass
    for reserva_id in reservas_creadas:
        try:
            await moc.eliminar("reservas", reserva_id)
        except Exception:
            pass


async def test_agrupa_por_proveedor_y_categoria(auto_factory, reserva_item_auto_factory):
    auto_a = await auto_factory(proveedor_agregador="expedia", categoria="SUV")
    auto_b = await auto_factory(proveedor_agregador="priceline", categoria="Económico")

    await reserva_item_auto_factory(auto_a["id"], estado_item="confirmado", precio_final=100.0)
    await reserva_item_auto_factory(auto_a["id"], estado_item="pendiente", precio_final=100.0)
    await reserva_item_auto_factory(auto_b["id"], estado_item="completado", precio_final=50.0)

    filas = await reporte_por_proveedor_categoria(dias=1)

    fila_expedia = next(f for f in filas if f["proveedor"] == "expedia" and f["categoria"] == "SUV")
    assert fila_expedia["reservas"] == 2
    assert fila_expedia["confirmadas"] == 1  # solo el "confirmado", el "pendiente" no cuenta
    assert fila_expedia["ingresos"] == 200.0

    fila_priceline = next(f for f in filas if f["proveedor"] == "priceline")
    assert fila_priceline["reservas"] == 1
    assert fila_priceline["confirmadas"] == 1
    assert fila_priceline["ingresos"] == 50.0


async def test_respeta_ventana_de_dias(auto_factory, reserva_item_auto_factory):
    auto = await auto_factory(proveedor_agregador="expedia", categoria="Compacto")
    await reserva_item_auto_factory(auto["id"])

    futuro = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=100)
    filas = await reporte_por_proveedor_categoria(dias=30, ahora=futuro)
    assert not any(f["proveedor"] == "expedia" and f["categoria"] == "compacto" for f in filas)


async def test_oferta_ya_reemplazada_no_rompe_el_reporte(pb, reserva_item_auto_factory):
    """RN-AUT-001: los precios de estas APIs son point-in-time — un
    reserva_item puede apuntar a un auto_id ya eliminado del catálogo
    (reemplazado por una corrida más nueva). No debe tumbar el reporte."""
    item = await reserva_item_auto_factory("id-que-ya-no-existe-en-autos_catalogo")
    filas = await reporte_por_proveedor_categoria(dias=1)
    assert isinstance(filas, list)  # no lanzó excepción


async def test_dashboard_requiere_permiso_admin(client, usuario_factory):
    pasajero = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})
    resp = await client.get("/backoffice/autos/reporte")
    assert resp.status_code == 403


async def test_dashboard_admin_ve_reporte(admin_client, auto_factory, reserva_item_auto_factory):
    auto = await auto_factory(proveedor_agregador="expedia", categoria="Lujo")
    await reserva_item_auto_factory(auto["id"])

    resp = await admin_client.get("/backoffice/autos/reporte?dias=1")
    assert resp.status_code == 200
    assert "expedia" in resp.text
    assert "lujo" in resp.text.lower()
