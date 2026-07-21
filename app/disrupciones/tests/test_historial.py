import httpx
from httpx import ASGITransport

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.main import app


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

async def test_pasajero_ve_solo_sus_notificaciones(pb, client, vuelo_con_reserva_confirmada, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario_a = vuelo_con_reserva_confirmada["usuario"]
    pasajero_a = vuelo_con_reserva_confirmada["pasajero"]
    reserva_a = vuelo_con_reserva_confirmada["reserva"]
    notificacion_a = await _crear_notificacion(pasajero_a["id"], reserva_a["id"], asunto="Notificación de A")

    _, pasajero_b = await pasajero_factory()
    vuelo_b = await vuelo_factory()
    tarifa_b = await tarifa_factory(vuelo_b["id"])
    reserva_b = await reserva_factory(pasajero_b["id"], vuelo_b["id"], tarifa_b["id"])
    notificacion_b = await _crear_notificacion(pasajero_b["id"], reserva_b["id"], asunto="Notificación de B")

    await _login(client, usuario_a)
    resp = await client.get("/notificaciones")
    assert resp.status_code == 200
    assert "Notificación de A" in resp.text
    assert "Notificación de B" not in resp.text

    await pb.delete_record("notificaciones", notificacion_a["id"])
    await pb.delete_record("notificaciones", notificacion_b["id"])


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

    await pb.delete_record("notificaciones", notificacion["id"])


async def test_agente_con_restriccion_nivel2_fuera_de_alcance_bloqueado(pb, usuario_factory, rol_agente):
    modulo_disrupciones = await pb.get_first("modulos", 'clave="disrupciones"')
    fila_nivel2 = await pb.create_record(
        "roles_permisos_tablas",
        {"rol_id": rol_agente["id"], "modulo_id": modulo_disrupciones["id"], "tabla": "disrupciones"},
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

async def test_filtros_instantaneos_por_canal_y_estado(pb, client, vuelo_con_reserva_confirmada):
    usuario = vuelo_con_reserva_confirmada["usuario"]
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    enviada = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="Ya enviada", estado_envio="enviado")
    fallida = await _crear_notificacion(pasajero["id"], reserva["id"], asunto="Aun fallida", estado_envio="fallido")

    await _login(client, usuario)
    resp = await client.get("/notificaciones?estado_envio=fallido")
    assert resp.status_code == 200
    assert "Aun fallida" in resp.text
    assert "Ya enviada" not in resp.text

    await pb.delete_record("notificaciones", enviada["id"])
    await pb.delete_record("notificaciones", fallida["id"])
