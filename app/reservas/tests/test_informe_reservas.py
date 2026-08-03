"""IS-09/IS-16 (auditoría de informes simples, sesión 2026-08-01) — umbral
explícito "próximas a vencer (<24h)" sobre el reporte de reservas (IS-08) y
mi cartera (IS-15), ya existentes; y exportar CSV, agregado sobre ambas
vistas por la regla general 5 del encargo."""

import datetime


async def test_reporte_filtro_urgentes_24h(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    ahora = datetime.datetime.now(datetime.timezone.utc)

    urgente = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"],
        fecha_expiracion_pago=(ahora + datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S.000Z"),
    )
    no_urgente = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"],
        fecha_expiracion_pago=(ahora + datetime.timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S.000Z"),
    )

    resp = await admin_client.get("/backoffice/reservas/reporte?urgentes_24h=1")
    assert resp.status_code == 200
    assert urgente["codigo_reserva"] in resp.text
    assert no_urgente["codigo_reserva"] not in resp.text


async def test_mi_cartera_filtro_urgentes_24h(
    agente_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    ahora = datetime.datetime.now(datetime.timezone.utc)
    agente_id = agente_client.agente_usuario["id"]

    urgente = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], agente_id=agente_id, canal="asistida",
        fecha_expiracion_pago=(ahora + datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S.000Z"),
    )
    no_urgente = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], agente_id=agente_id, canal="asistida",
        fecha_expiracion_pago=(ahora + datetime.timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S.000Z"),
    )

    resp = await agente_client.get("/backoffice/reservas/mi-cartera?urgentes_24h=1")
    assert resp.status_code == 200
    assert urgente["codigo_reserva"] in resp.text
    assert no_urgente["codigo_reserva"] not in resp.text


async def test_exportar_reporte_reservas_csv(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])

    resp = await admin_client.get("/backoffice/reservas/reporte/exportar")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert resp.text.splitlines()[0] == (
        "codigo_reserva,pasajero,estado,canal,total_pagar,fecha_reserva,horas_para_vencer"
    )
    assert reserva["codigo_reserva"] in resp.text


async def test_exportar_mi_cartera_csv_respeta_alcance(
    agente_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    agente_id = agente_client.agente_usuario["id"]

    mia = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], agente_id=agente_id, canal="asistida")
    de_otro = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], agente_id="otro-agente-id", canal="asistida")

    resp = await agente_client.get("/backoffice/reservas/mi-cartera/exportar")
    assert resp.status_code == 200
    assert mia["codigo_reserva"] in resp.text
    assert de_otro["codigo_reserva"] not in resp.text
