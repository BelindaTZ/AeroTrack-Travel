"""RF-DIS-002 (CU-O28) — monitorea la bandeja de correo y convierte los
avisos de aerolínea válidos en disrupciones (fuente `monitor_correo`).
"""

import datetime

from app.disrupciones.integrations.gmail_client import GmailClient
from app.disrupciones.integrations.notification_sender import NotificationSender
from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.disrupciones.services.deteccion_service import parsear_correo_a_disrupcion
from app.disrupciones.services.notificacion_service import procesar_disrupcion
from app.seguridad.services.audit_service import AuditService
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.estado_service import actualizar_estado

_TIPO_CAMBIO_A_ESTADO = {"retraso": "retrasado", "cancelacion": "cancelado", "desvio": "desviado"}


async def monitorear_correo(client: GmailClient, sender: NotificationSender, ultimas_horas: int = 24) -> dict:
    """Retorna `{"correos_leidos", "disrupciones_creadas", "descartados"}`."""
    repo = DisrupcionesRepository()
    vuelos_repo = VuelosRepository()

    correos = await client.leer_correos_nuevos(ultimas_horas)
    resumen = {"correos_leidos": len(correos), "disrupciones_creadas": 0, "descartados": 0}

    for correo in correos:
        detectado = await parsear_correo_a_disrupcion(correo)
        if detectado is None:
            resumen["descartados"] += 1
            continue

        vuelo = await vuelos_repo.obtener_vuelo(detectado["vuelo_id"])
        nuevo_estado = _TIPO_CAMBIO_A_ESTADO.get(detectado["tipo_cambio"])
        if vuelo is not None and nuevo_estado is not None and vuelo["estado"] == nuevo_estado:
            # Ya se registró este mismo cambio (p. ej. la API real lo detectó
            # primero) — no duplicar la disrupción activa.
            continue

        ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
        disrupcion = await repo.crear_disrupcion(
            {
                "vuelo_id": detectado["vuelo_id"],
                "fuente_deteccion": "monitor_correo",
                "tipo_cambio": detectado["tipo_cambio"],
                "estado": "activa",
                "detalle": detectado["detalle"],
                "fecha_deteccion": ahora_iso,
            }
        )
        resumen["disrupciones_creadas"] += 1

        if nuevo_estado is not None:
            await actualizar_estado(detectado["vuelo_id"], nuevo_estado, origen="automatico")

        await AuditService().insertar(
            "disrupcion_detectada",
            "disrupciones",
            registro_id=disrupcion["id"],
            detalle={
                "fuente_deteccion": "monitor_correo",
                "tipo_cambio": detectado["tipo_cambio"],
                "vuelo_id": detectado["vuelo_id"],
            },
        )

        # REG-E1: ninguna disrupción detectada queda sin su intento de notificación.
        await procesar_disrupcion(disrupcion["id"], sender)

    return resumen
