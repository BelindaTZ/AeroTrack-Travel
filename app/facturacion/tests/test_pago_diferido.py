"""RF-FAC-012 (CU-O86) — Stripe authorize-then-capture para "Reservar
hotel sin pagar ahora" (RF-HOT-009, CU-O60). Llamadas reales a Stripe test
mode, mismo criterio que `test_pago.py` — nunca mockeado."""

import datetime
import uuid

import httpx
import pytest
from httpx import ASGITransport

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.services.pago_service import (
    PagoNoAutorizado,
    PagoNoEncontrado,
    capturar_pago_diferido,
)
from app.main import app
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303


@pytest.fixture
async def reserva_hotel_diferido_factory():
    """Reserva de hotel con `reserva_items.modalidad_pago = pago_diferido`
    — sin `vuelo_id`/`tarifa_id` (dual-write legado no aplica a hoteles)."""
    reservas_creadas: list[str] = []
    items_creados: list[str] = []

    async def _crear(pasajero_id: str, total_pagar: float = 150.0) -> dict:
        repo = ReservasRepository()
        ahora = datetime.datetime.now(datetime.timezone.utc)
        reserva = await repo.crear_reserva(
            {
                "codigo_reserva": f"HTL{uuid.uuid4().hex[:8].upper()}",
                "pasajero_titular_id": pasajero_id,
                "canal": "autoservicio",
                "estado": "pendiente_pago",
                "total_pagar": total_pagar,
                "fecha_reserva": ahora.strftime("%Y-%m-%d %H:%M:%S.000Z"),
                "fecha_expiracion_pago": (ahora + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S.000Z"),
            },
        )
        reservas_creadas.append(reserva["id"])
        item = await repo.crear_item(
            {
                "reserva_id": reserva["id"], "tipo_producto": "hotel",
                "modalidad_pago": "pago_diferido", "precio_final": total_pagar,
                "cantidad": 1, "estado_item": "pendiente",
            },
        )
        items_creados.append(item["id"])
        return reserva

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


async def _limpiar_pago_y_documentos(pago_id: str, reserva_id: str) -> None:
    repo = FacturacionRepository()
    factura = await repo.factura_de_pago(pago_id)
    if factura is not None:
        await moc.eliminar("facturas", factura["id"])
    comisiones = await repo.listar_comisiones()
    comision = next((c for c in comisiones if c.get("reserva_id") == reserva_id), None)
    if comision is not None:
        await moc.eliminar("comisiones", comision["id"])
    await moc.eliminar("pagos", pago_id)


async def test_reserva_con_item_pago_diferido_autoriza_en_vez_de_cobrar(
    client, pasajero_factory, reserva_hotel_diferido_factory
):
    usuario, pasajero = await pasajero_factory()
    reserva = await reserva_hotel_diferido_factory(pasajero["id"], total_pagar=150.0)

    facturacion_repo = FacturacionRepository()

    await _login(client, usuario)
    resp = await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303

    # RF-HOT-009: la reserva se confirma sin cobrar de inmediato.
    reserva_actualizada = await ReservasRepository().obtener_reserva(reserva["id"])
    assert reserva_actualizada["estado"] == "confirmada"

    pagos = await facturacion_repo.pagos_de_reserva(reserva["id"])
    pago = pagos[0]
    assert pago is not None
    assert pago["estado"] == "autorizado"
    assert pago["captura_diferida"] is True
    assert pago["fecha_autorizacion"]
    assert not pago.get("fecha_pago")
    assert pago["stripe_payment_intent_id"].startswith("pi_")

    # CU-O33 ata factura/voucher a un pago EXITOSO, no a uno autorizado.
    factura = await facturacion_repo.factura_de_pago(pago["id"])
    assert factura is None

    await _limpiar_pago_y_documentos(pago["id"], reserva["id"])


async def test_reintentar_pago_de_reserva_ya_autorizada_es_idempotente(
    client, pasajero_factory, reserva_hotel_diferido_factory
):
    usuario, pasajero = await pasajero_factory()
    reserva = await reserva_hotel_diferido_factory(pasajero["id"], total_pagar=150.0)

    await _login(client, usuario)
    await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})

    pagos = await FacturacionRepository().pagos_de_reserva(reserva["id"])
    assert len(pagos) == 1  # RNF-FAC-002: no se autorizó dos veces

    pago = pagos[0]
    await _limpiar_pago_y_documentos(pago["id"], reserva["id"])


async def test_capturar_pago_diferido_completa_cobro_y_emite_factura(
    client, pasajero_factory, reserva_hotel_diferido_factory
):
    usuario, pasajero = await pasajero_factory()
    reserva = await reserva_hotel_diferido_factory(pasajero["id"], total_pagar=150.0)

    facturacion_repo = FacturacionRepository()

    await _login(client, usuario)
    await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    pagos = await facturacion_repo.pagos_de_reserva(reserva["id"])
    pago = pagos[0]

    pago_capturado = await capturar_pago_diferido(pago["id"])
    assert pago_capturado["estado"] == "exitoso"
    assert pago_capturado["fecha_pago"]

    factura = await facturacion_repo.factura_de_pago(pago["id"])
    assert factura is not None

    await _limpiar_pago_y_documentos(pago["id"], reserva["id"])


async def test_capturar_pago_no_autorizado_rechaza(pb, pasajero_factory, reserva_hotel_diferido_factory):
    _, pasajero = await pasajero_factory()
    reserva = await reserva_hotel_diferido_factory(pasajero["id"])
    metodo = await pb.get_first("metodos_pago", "activo=true")
    repo = FacturacionRepository()
    pago = await repo.crear_pago(
        {
            "reserva_id": reserva["id"], "monto": 150.0, "moneda": "USD", "metodo_pago_id": metodo["id"],
            "stripe_payment_intent_id": "pi_test_ya_exitoso", "estado": "exitoso",
        },
    )
    try:
        with pytest.raises(PagoNoAutorizado):
            await capturar_pago_diferido(pago["id"])
    finally:
        await moc.eliminar("pagos", pago["id"])


async def test_capturar_pago_inexistente_rechaza():
    with pytest.raises(PagoNoEncontrado):
        await capturar_pago_diferido("id-que-no-existe")


async def test_backoffice_pagos_diferidos_requiere_permiso_admin(client, usuario_factory):
    pasajero = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})
    resp = await client.get("/backoffice/pagos-diferidos")
    assert resp.status_code == 403


async def test_backoffice_pagos_diferidos_admin_ve_pago_autorizado(
    client, pasajero_factory, reserva_hotel_diferido_factory, usuario_factory, rol_administrador
):
    # `client`/`admin_client` comparten cookies — para tener pasajero Y
    # admin autenticados a la vez se arma un segundo cliente independiente
    # (mismo criterio que `test_desactivar_cuenta_fuerza_cierre_de_sesion`).
    usuario, pasajero = await pasajero_factory()
    reserva = await reserva_hotel_diferido_factory(pasajero["id"], total_pagar=150.0)

    await _login(client, usuario)
    await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    pagos = await FacturacionRepository().pagos_de_reserva(reserva["id"])
    pago = pagos[0]

    admin = await usuario_factory(tipo_actor="administrador", rol_id=rol_administrador["id"])
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as admin_http:
        await admin_http.post("/login", data={"email": admin["email"], "password": admin["_password"]})
        resp = await admin_http.get("/backoffice/pagos-diferidos")

    assert resp.status_code == 200
    assert reserva["codigo_reserva"] in resp.text

    await _limpiar_pago_y_documentos(pago["id"], reserva["id"])


async def test_backoffice_capturar_endpoint_marca_exitoso(
    client, pasajero_factory, reserva_hotel_diferido_factory, usuario_factory, rol_administrador
):
    usuario, pasajero = await pasajero_factory()
    reserva = await reserva_hotel_diferido_factory(pasajero["id"], total_pagar=150.0)

    facturacion_repo = FacturacionRepository()

    await _login(client, usuario)
    await client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    pagos = await facturacion_repo.pagos_de_reserva(reserva["id"])
    pago = pagos[0]

    admin = await usuario_factory(tipo_actor="administrador", rol_id=rol_administrador["id"])
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as admin_http:
        await admin_http.post("/login", data={"email": admin["email"], "password": admin["_password"]})
        resp = await admin_http.post(f"/backoffice/pagos-diferidos/{pago['id']}/capturar")

    assert resp.status_code == 303

    pago_actualizado = await facturacion_repo.obtener_pago(pago["id"])
    assert pago_actualizado["estado"] == "exitoso"

    await _limpiar_pago_y_documentos(pago["id"], reserva["id"])
