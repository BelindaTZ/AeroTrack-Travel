"""RF-DIS-004 (CU-O30) — punto de convergencia de las 3 fuentes de
detección: genera la notificación real a cada pasajero afectado, aplicando
precedencia/deduplicación (RN-DIS-002) y reembolso condicionado a
cancelación (RN-DIS-003).

Alcance explícito (no ampliado más allá de lo escrito en la spec): una
disrupción de tipo `cancelacion` dispara el reembolso según la política de
la tarifa (`<<extend>>` CU-O37) — NO cancela la reserva en sí (eso no está
en el `<<extend>>` documentado de CU-O30; cancelar la reserva sigue siendo
una acción del pasajero/agente vía CU-O24).
"""

import datetime
import logging

from app.disrupciones.integrations.notification_sender import NotificationSender
from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.facturacion.services.reembolso_service import PagoNoEncontrado, ReembolsoNoAplicable, procesar_reembolso
from app.disrupciones.services.reintento_service import reintentar_notificacion
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.vuelos.repositories.vuelos_repo import VuelosRepository

logger = logging.getLogger("disrupciones.notificacion")

_PRECEDENCIA = {"api_real": 0, "monitor_correo": 1, "simulador_estadistico": 2}

_TEXTO_POR_TIPO = {
    "retraso": "Tu vuelo {numero_vuelo} sufrió un retraso.",
    "cancelacion": "Tu vuelo {numero_vuelo} fue cancelado por la aerolínea.",
    "cambio_horario": "El horario de tu vuelo {numero_vuelo} cambió.",
    "cambio_puerta": "La puerta de embarque de tu vuelo {numero_vuelo} cambió.",
    "desvio": "Tu vuelo {numero_vuelo} fue desviado a otro destino.",
}

_CLAVE_PLANTILLA_POR_TIPO = {
    "retraso": "disrupciones.plantilla_retraso",
    "cancelacion": "disrupciones.plantilla_cancelacion",
    "cambio_horario": "disrupciones.plantilla_cambio_horario",
    "cambio_puerta": "disrupciones.plantilla_cambio_puerta",
    "desvio": "disrupciones.plantilla_desvio",
}


async def _plantilla_texto(repo: DisrupcionesRepository, tipo_cambio: str) -> str:
    """WP-08 (ampliación de sesión 2026-08-01) — editable desde
    Configuración del sistema; `_TEXTO_POR_TIPO` sigue siendo el fallback
    si la clave todavía no está sembrada."""
    config = await repo.config(_CLAVE_PLANTILLA_POR_TIPO[tipo_cambio])
    return config["valor"] if config else _TEXTO_POR_TIPO[tipo_cambio]


async def _plantilla_asunto(repo: DisrupcionesRepository) -> str:
    config = await repo.config("disrupciones.plantilla_asunto")
    return config["valor"] if config else "AeroTrack Travel — {codigo_reserva}"


class DisrupcionNoEncontrada(Exception):
    pass


def aplicar_precedencia(disrupciones: list[dict]) -> list[dict]:
    """RN-DIS-002 (QP-02) — función pura: de varias disrupciones activas
    sobre el mismo `(vuelo_id, tipo_cambio)`, retorna solo la de mayor
    precedencia (`api_real` > `monitor_correo` > `simulador_estadistico`)."""
    ganadoras: dict[tuple[str, str], dict] = {}
    for d in disrupciones:
        clave = (d["vuelo_id"], d["tipo_cambio"])
        actual = ganadoras.get(clave)
        if actual is None or _PRECEDENCIA[d["fuente_deteccion"]] < _PRECEDENCIA[actual["fuente_deteccion"]]:
            ganadoras[clave] = d
    return list(ganadoras.values())


async def procesar_disrupcion(disrupcion_id: str, sender: NotificationSender) -> dict:
    repo = DisrupcionesRepository()
    reservas_repo = ReservasRepository()
    pasajeros_repo = PasajerosRepository()

    disrupcion = await repo.obtener_disrupcion(disrupcion_id)
    if disrupcion is None:
        raise DisrupcionNoEncontrada()

    # RN-DIS-002: si otra disrupción activa sobre el mismo vuelo+tipo tiene
    # mayor precedencia, esta no genera notificación por su cuenta — la de
    # mayor precedencia ya lo hizo (o lo hará) por ambas.
    activas = await repo.disrupciones_de_vuelo_y_tipo(disrupcion["vuelo_id"], disrupcion["tipo_cambio"])
    if activas:
        ganadora = aplicar_precedencia(activas)[0]
        if ganadora["id"] != disrupcion_id:
            return {"notificaciones_generadas": 0, "motivo": "precedencia_cede_a_otra_fuente"}

    vuelo = await VuelosRepository().obtener_vuelo(disrupcion["vuelo_id"])
    numero_vuelo = vuelo["numero_vuelo"] if vuelo else disrupcion["vuelo_id"]

    reservas = await reservas_repo.listar_reservas_confirmadas_de_vuelo(disrupcion["vuelo_id"])
    generadas = 0

    for reserva in reservas:
        vinculos = await reservas_repo.pasajeros_de_reserva(reserva["id"])
        pasajero_ids = {v["pasajero_id"] for v in vinculos}
        pasajero_ids.add(reserva["pasajero_titular_id"])

        for pasajero_id in pasajero_ids:
            # Deduplicación: no generar dos notificaciones para el mismo
            # pasajero sobre la misma disrupción (reintentos de scheduler).
            if await repo.notificaciones_de_disrupcion_y_pasajero(disrupcion_id, pasajero_id):
                continue

            pasajero = await pasajeros_repo.obtener_pasajero(pasajero_id)
            if pasajero is None:
                continue
            usuario = await pasajeros_repo.usuario_por_id(pasajero["usuario_id"])
            if usuario is None:
                continue

            texto_plantilla = await _plantilla_texto(repo, disrupcion["tipo_cambio"])
            texto = texto_plantilla.format(numero_vuelo=numero_vuelo)
            asunto_plantilla = await _plantilla_asunto(repo)
            asunto = asunto_plantilla.format(codigo_reserva=reserva["codigo_reserva"])
            canal = "email"
            ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")

            notificacion = await repo.crear_notificacion(
                {
                    "pasajero_id": pasajero_id,
                    "reserva_id": reserva["id"],
                    "disrupcion_id": disrupcion_id,
                    "canal": canal,
                    "asunto": asunto,
                    "contenido": texto,
                    "estado_envio": "pendiente",
                    "intentos_envio": 1,
                }
            )

            try:
                exitoso = await sender.enviar(canal, usuario["email"], notificacion["asunto"], texto)
            except Exception:
                # RNF-DIS-003: aislado del resto del ciclo — un proveedor
                # caído no debe impedir procesar las demás notificaciones.
                logger.warning("Fallo al enviar notificación a %s", usuario["email"], exc_info=True)
                exitoso = False

            await repo.actualizar_notificacion(
                notificacion["id"],
                {"estado_envio": "enviado" if exitoso else "fallido", "fecha_envio": ahora_iso},
            )
            generadas += 1

            if not exitoso:
                # RF-DIS-006: el primer reintento se dispara de inmediato,
                # no se espera al siguiente ciclo del scheduler.
                await reintentar_notificacion(notificacion["id"], sender)

        # RN-DIS-003: el reembolso se evalúa una sola vez por reserva
        # (no por pasajero notificado), y solo si el tipo es cancelación.
        if disrupcion["tipo_cambio"] == "cancelacion":
            try:
                await procesar_reembolso(reserva["id"], "Cancelación por disrupción de vuelo")
            except (PagoNoEncontrado, ReembolsoNoAplicable):
                pass

    await AuditService().insertar(
        "notificaciones_generadas",
        "disrupciones",
        registro_id=disrupcion_id,
        detalle={"cantidad": generadas, "tipo_cambio": disrupcion["tipo_cambio"]},
    )
    return {"notificaciones_generadas": generadas}
