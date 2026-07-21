"""RF-DIS-006 (CU-O46), RN-DIS-006 — reintento de envío de una notificación
fallida, con límite de intentos configurado en `configuracion_sistema`
(nunca reintento silencioso indefinido).
"""

import datetime
import logging

from app.disrupciones.integrations.notification_sender import NotificationSender
from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.seguridad.services.audit_service import AuditService

logger = logging.getLogger("disrupciones.reintento")


class NotificacionNoEncontrada(Exception):
    pass


async def _max_reintentos() -> int:
    repo = DisrupcionesRepository()
    config = await repo.config("notificaciones.max_reintentos")
    if config is None:
        raise RuntimeError("configuracion_sistema.notificaciones.max_reintentos no está sembrado")
    return int(config["valor"])


async def reintentar_notificacion(notificacion_id: str, sender: NotificationSender) -> dict:
    repo = DisrupcionesRepository()
    pasajeros_repo = PasajerosRepository()

    notificacion = await repo.obtener_notificacion(notificacion_id)
    if notificacion is None:
        raise NotificacionNoEncontrada()

    if notificacion["estado_envio"] != "fallido":
        return {"reintentado": False, "estado_envio": notificacion["estado_envio"]}

    max_reintentos = await _max_reintentos()
    intentos_previos = notificacion.get("intentos_envio") or 0

    if intentos_previos >= max_reintentos:
        # RN-DIS-006: límite ya alcanzado antes de este reintento ->
        # constancia definitiva, sin un intento más.
        return await _marcar_definitivo(repo, notificacion_id, intentos_previos)

    pasajero = await pasajeros_repo.obtener_pasajero(notificacion["pasajero_id"])
    usuario = await pasajeros_repo.usuario_por_id(pasajero["usuario_id"]) if pasajero else None
    nuevos_intentos = intentos_previos + 1

    if usuario is None:
        return await _marcar_definitivo(repo, notificacion_id, nuevos_intentos)

    try:
        exitoso = await sender.enviar(
            notificacion["canal"], usuario["email"], notificacion["asunto"], notificacion["contenido"]
        )
    except Exception:
        # RNF-DIS-003: la caída del proveedor (canal no soportado, timeout,
        # red caída, scope OAuth insuficiente — el hallazgo real de esta
        # sesión, ver errores-conocidos.md) nunca debe propagarse: se trata
        # como un intento fallido más, aislado del resto del sistema.
        logger.warning("Fallo al reintentar notificación %s", notificacion_id, exc_info=True)
        exitoso = False

    if exitoso:
        ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
        await repo.actualizar_notificacion(
            notificacion_id,
            {"estado_envio": "enviado", "intentos_envio": nuevos_intentos, "fecha_envio": ahora_iso},
        )
        return {"reintentado": True, "estado_envio": "enviado"}

    if nuevos_intentos >= max_reintentos:
        return await _marcar_definitivo(repo, notificacion_id, nuevos_intentos)

    await repo.actualizar_notificacion(
        notificacion_id, {"estado_envio": "fallido", "intentos_envio": nuevos_intentos}
    )
    return {"reintentado": True, "estado_envio": "fallido"}


async def _marcar_definitivo(repo: DisrupcionesRepository, notificacion_id: str, intentos: int) -> dict:
    await repo.actualizar_notificacion(
        notificacion_id, {"estado_envio": "fallido_definitivo", "intentos_envio": intentos}
    )
    await AuditService().insertar(
        "notificacion_fallo_definitivo",
        "notificaciones",
        registro_id=notificacion_id,
        detalle={"intentos": intentos},
    )
    return {"reintentado": False, "estado_envio": "fallido_definitivo"}
