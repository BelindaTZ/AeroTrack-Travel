from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.disrupciones.services.reintento_service import reintentar_notificacion
from app.shared import minio_operational_client as moc


async def _crear_notificacion_fallida(pasajero_id: str, reserva_id: str, intentos_envio: int) -> dict:
    repo = DisrupcionesRepository()
    return await repo.crear_notificacion(
        {
            "pasajero_id": pasajero_id,
            "reserva_id": reserva_id,
            "canal": "email",
            "asunto": "AeroTrack Travel — prueba",
            "contenido": "Contenido de prueba",
            "estado_envio": "fallido",
            "intentos_envio": intentos_envio,
        }
    )


# ── CHK007, CHK022 — reintenta según política, deja constancia definitiva ──

async def test_notificacion_fallida_se_reintenta_y_puede_recuperarse(
    vuelo_con_reserva_confirmada, notification_sender_falso
):
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    notificacion = await _crear_notificacion_fallida(pasajero["id"], reserva["id"], intentos_envio=1)

    notification_sender_falso.exitoso = True
    resultado = await reintentar_notificacion(notificacion["id"], notification_sender_falso)
    assert resultado == {"reintentado": True, "estado_envio": "enviado"}

    actualizada = await DisrupcionesRepository().obtener_notificacion(notificacion["id"])
    assert actualizada["estado_envio"] == "enviado"
    assert actualizada["intentos_envio"] == 2

    await moc.eliminar("notificaciones", notificacion["id"])


async def test_reintentos_agotados_quedan_como_fallo_definitivo_visible(
    pb, vuelo_con_reserva_confirmada, notification_sender_falso
):
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    # max_reintentos sembrado = 3 — ya lleva 2 intentos previos.
    notificacion = await _crear_notificacion_fallida(pasajero["id"], reserva["id"], intentos_envio=2)

    notification_sender_falso.exitoso = False
    resultado = await reintentar_notificacion(notificacion["id"], notification_sender_falso)
    assert resultado["estado_envio"] == "fallido_definitivo"

    actualizada = await DisrupcionesRepository().obtener_notificacion(notificacion["id"])
    assert actualizada["estado_envio"] == "fallido_definitivo"
    assert actualizada["intentos_envio"] == 3

    registro = await pb.get_first(
        "auditoria", f'accion="notificacion_fallo_definitivo" && registro_id="{notificacion["id"]}"'
    )
    assert registro is not None  # visible para Agente/Administrador (RF-DIS-006)

    await pb.delete_record("auditoria", registro["id"])
    await moc.eliminar("notificaciones", notificacion["id"])


# ── CHK013, RN-DIS-006 — límite explícito, nunca reintento indefinido ────

async def test_no_hay_reintento_indefinido_tras_agotar_el_limite(
    vuelo_con_reserva_confirmada, notification_sender_falso
):
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    notificacion = await _crear_notificacion_fallida(pasajero["id"], reserva["id"], intentos_envio=3)

    resultado = await reintentar_notificacion(notificacion["id"], notification_sender_falso)
    assert resultado == {"reintentado": False, "estado_envio": "fallido_definitivo"}
    assert len(notification_sender_falso.enviados) == 0  # ni siquiera intenta enviar — ya estaba agotado

    # Un segundo llamado (simulando que el scheduler lo vuelve a intentar)
    # tampoco hace nada — no queda en "fallido" para volver a calificar.
    actualizada = await DisrupcionesRepository().obtener_notificacion(notificacion["id"])
    resultado_2 = await reintentar_notificacion(notificacion["id"], notification_sender_falso)
    assert resultado_2 == {"reintentado": False, "estado_envio": actualizada["estado_envio"]}

    await moc.eliminar("notificaciones", notificacion["id"])


# ── CHK016, RNF-DIS-003 — aislamiento de fallos del canal de envío ───────

async def test_canal_no_disponible_no_lanza_excepcion_ni_afecta_el_resto(
    vuelo_con_reserva_confirmada,
):
    """Simula la caída total del proveedor (Gmail send con scope insuficiente,
    hallazgo real de esta sesión — ver errores-conocidos.md): el reintento
    debe degradarse a `fallido`, nunca propagar la excepción hacia arriba."""
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    notificacion = await _crear_notificacion_fallida(pasajero["id"], reserva["id"], intentos_envio=1)

    class SenderCaido:
        async def enviar(self, canal, destino, asunto, cuerpo):
            raise ConnectionError("Proveedor de correo caído (doble de prueba)")

    resultado = await reintentar_notificacion(notificacion["id"], SenderCaido())
    assert resultado == {"reintentado": True, "estado_envio": "fallido"}

    # El servicio de reintento en sí no debe quedar en un estado roto — una
    # notificación fallida sigue siendo reintentable en el próximo ciclo.
    actualizada = await DisrupcionesRepository().obtener_notificacion(notificacion["id"])
    assert actualizada["estado_envio"] == "fallido"
    assert actualizada["intentos_envio"] == 2

    await moc.eliminar("notificaciones", notificacion["id"])
