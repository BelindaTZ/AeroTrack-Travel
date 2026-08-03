import httpx
from httpx import ASGITransport

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.main import app
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303


async def _crear_notificacion(pasajero_id: str, reserva_id: str, **extra) -> dict:
    repo = DisrupcionesRepository()
    data = {
        "pasajero_id": pasajero_id,
        "reserva_id": reserva_id,
        "canal": "email",
        "asunto": "AeroTrack Travel — prueba",
        "contenido": "Contenido de prueba",
        "estado_envio": "enviado",
    }
    data.update(extra)
    return await repo.crear_notificacion(data)


# ── CHK006 — pasajero ve solo las suyas ─────────────────────────────────

async def test_pasajero_ve_solo_sus_notificaciones(pb, client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    # CU-T49: el historial solo muestra reservas cuyo vuelo YA salió — ambos
    # vuelos se crean con `fecha_salida` pasada a propósito (el default de
    # `vuelo_factory` es futuro, 2027-01-01, pensado para el flujo de
    # disrupciones activas, no para "historial").
    usuario_a, pasajero_a = await pasajero_factory()
    vuelo_a = await vuelo_factory(fecha_salida="2026-01-01")
    tarifa_a = await tarifa_factory(vuelo_a["id"])
    reserva_a = await reserva_factory(pasajero_a["id"], vuelo_a["id"], tarifa_a["id"], estado="confirmada")
    notificacion_a = await _crear_notificacion(pasajero_a["id"], reserva_a["id"], asunto="Notificación de A")

    _, pasajero_b = await pasajero_factory()
    vuelo_b = await vuelo_factory(fecha_salida="2026-01-01")
    tarifa_b = await tarifa_factory(vuelo_b["id"])
    reserva_b = await reserva_factory(pasajero_b["id"], vuelo_b["id"], tarifa_b["id"])
    notificacion_b = await _crear_notificacion(pasajero_b["id"], reserva_b["id"], asunto="Notificación de B")

    await _login(client, usuario_a)
    resp = await client.get("/notificaciones")
    assert resp.status_code == 200
    assert "Notificación de A" in resp.text
    assert "Notificación de B" not in resp.text

    await moc.eliminar("notificaciones", notificacion_a["id"])
    await moc.eliminar("notificaciones", notificacion_b["id"])


# ── CHK006 — Agente dentro/fuera de alcance RBAC ────────────────────────

async def test_agente_ve_notificaciones_backoffice_dentro_de_su_alcance(
    pb, admin_client, vuelo_con_reserva_confirmada
):
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    notificacion = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="Notificación backoffice")

    resp = await admin_client.get("/backoffice/notificaciones")
    assert resp.status_code == 200
    assert "Notificación backoffice" in resp.text

    await moc.eliminar("notificaciones", notificacion["id"])


async def test_agente_con_restriccion_nivel2_fuera_de_alcance_bloqueado(pb, usuario_factory, rol_agente):
    modulo_disrupciones = await pb.get_first("modulos", 'clave="disrupciones"')
    fila_nivel2 = await pb.create_record(
        "roles_permisos_tablas",
        {"rol_id": rol_agente["id"], "modulo_id": modulo_disrupciones["id"], "tabla": "disrupciones", "accion": "ver"},
    )
    try:
        agente = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente_agente:
            await _login(cliente_agente, agente)
            resp = await cliente_agente.get("/backoffice/notificaciones")
            assert resp.status_code == 403
    finally:
        await pb.delete_record("roles_permisos_tablas", fila_nivel2["id"])


# ── REG-J9 — filtros instantáneos sin botón "Aplicar" ───────────────────

async def test_filtros_instantaneos_por_canal_y_estado(pb, client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    # CU-T49: mismo motivo que arriba — el historial solo muestra reservas
    # de vuelos ya salidos, así que este vuelo se crea con fecha pasada.
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory(fecha_salida="2026-01-01")
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada")
    enviada = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="Ya enviada", estado_envio="enviado")
    fallida = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="Aun fallida", estado_envio="fallido")

    await _login(client, usuario)
    resp = await client.get("/notificaciones?estado_envio=fallido")
    assert resp.status_code == 200
    assert "Aun fallida" in resp.text
    assert "Ya enviada" not in resp.text

    await moc.eliminar("notificaciones", enviada["id"])
    await moc.eliminar("notificaciones", fallida["id"])


# ── IS-12 — filtro de período, paginación y exportar CSV (backoffice) ───

async def test_backoffice_filtro_periodo(pb, admin_client, vuelo_con_reserva_confirmada):
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    vieja = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="Notificación vieja")
    await moc.actualizar_con_reintento(
        "notificaciones", vieja["id"], lambda actual: {**actual, "created": "2020-01-01 00:00:00.000Z"}
    )
    nueva = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="Notificación reciente")

    try:
        resp = await admin_client.get("/backoffice/notificaciones?desde=2025-01-01")
        assert resp.status_code == 200
        assert "Notificación reciente" in resp.text
        assert "Notificación vieja" not in resp.text

        resp = await admin_client.get("/backoffice/notificaciones?hasta=2020-06-01")
        assert resp.status_code == 200
        assert "Notificación vieja" in resp.text
        assert "Notificación reciente" not in resp.text
    finally:
        await moc.eliminar("notificaciones", vieja["id"])
        await moc.eliminar("notificaciones", nueva["id"])


async def test_backoffice_paginacion(pb, admin_client, vuelo_con_reserva_confirmada):
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    notificacion = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="Notificación paginada")

    try:
        resp = await admin_client.get("/backoffice/notificaciones?page=1")
        assert resp.status_code == 200
        assert "Notificación paginada" in resp.text

        # página fuera de rango — `paginar()` la clampa, no debe romper.
        resp = await admin_client.get("/backoffice/notificaciones?page=999")
        assert resp.status_code == 200
    finally:
        await moc.eliminar("notificaciones", notificacion["id"])


async def test_backoffice_exportar_csv_respeta_filtros(pb, admin_client, vuelo_con_reserva_confirmada):
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    enviada = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="Para exportar", estado_envio="enviado")
    fallida = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="No exportar", estado_envio="fallido")

    try:
        resp = await admin_client.get("/backoffice/notificaciones/exportar?estado_envio=enviado")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "attachment" in resp.headers["content-disposition"]
        assert "Para exportar" in resp.text
        assert "No exportar" not in resp.text
        assert resp.text.splitlines()[0] == "fecha,codigo_reserva,canal,asunto,estado_envio"
    finally:
        await moc.eliminar("notificaciones", enviada["id"])
        await moc.eliminar("notificaciones", fallida["id"])


async def test_backoffice_exportar_csv_bloqueado_sin_permiso(pb, usuario_factory, rol_agente):
    modulo_disrupciones = await pb.get_first("modulos", 'clave="disrupciones"')
    fila_nivel2 = await pb.create_record(
        "roles_permisos_tablas",
        {"rol_id": rol_agente["id"], "modulo_id": modulo_disrupciones["id"], "tabla": "disrupciones", "accion": "ver"},
    )
    try:
        agente = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente_agente:
            await _login(cliente_agente, agente)
            resp = await cliente_agente.get("/backoffice/notificaciones/exportar")
            assert resp.status_code == 403
    finally:
        await pb.delete_record("roles_permisos_tablas", fila_nivel2["id"])
