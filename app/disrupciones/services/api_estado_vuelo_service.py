"""RF-DIS-001 (CU-O27) — consulta periódica a la API real de estado de
vuelo, con degradación ordenada (RNF-DIS-001/002).
"""

import datetime
import logging

from app.disrupciones.integrations.flight_status_client import FlightStatusClient
from app.disrupciones.integrations.notification_sender import NotificationSender
from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.disrupciones.services.notificacion_service import procesar_disrupcion
from app.seguridad.services.audit_service import AuditService
from app.shared.pocketbase_client import get_pocketbase_client
from app.vuelos.services.estado_service import actualizar_estado

logger = logging.getLogger("disrupciones.api_estado_vuelo")

# `estado_api` -> `tipo_cambio` de `disrupciones` — solo estos 3 valores
# representan una disrupción real; "programado"/"completado" son
# progresión normal del vuelo, no un cambio que notificar.
_TIPO_CAMBIO_POR_ESTADO = {"retrasado": "retraso", "cancelado": "cancelacion", "desviado": "desvio"}


async def _vuelos_candidatos(ventana_horas: int) -> list[dict]:
    client = get_pocketbase_client()
    ahora = datetime.datetime.now(datetime.timezone.utc)
    limite = ahora + datetime.timedelta(hours=ventana_horas)
    resultado = await client.list_records(
        "vuelos_catalogo",
        {
            "filter": (
                f'estado != "completado" && estado != "cancelado" '
                f'&& fecha_salida >= "{ahora.strftime("%Y-%m-%d %H:%M:%S.000Z")}" '
                f'&& fecha_salida <= "{limite.strftime("%Y-%m-%d %H:%M:%S.000Z")}"'
            ),
            "perPage": 200,
        },
    )
    return resultado["items"]


async def consultar_estados_cercanos(client: FlightStatusClient, sender: NotificationSender) -> dict:
    """Retorna un resumen `{"consultados", "disrupciones_creadas", "degradado"}`
    — nunca lanza: una API caída se registra como degradación (RNF-DIS-001) y
    el resto de los vuelos candidatos se sigue procesando con normalidad."""
    repo = DisrupcionesRepository()
    config = await repo.config("disrupciones.umbral_api_real_horas")
    ventana_horas = int(config["valor"]) if config else 72

    resumen = {"consultados": 0, "disrupciones_creadas": 0, "degradado": False}

    if not await client.esta_disponible():
        resumen["degradado"] = True
        await AuditService().insertar(
            "degradacion_api_estado_vuelo",
            "disrupciones",
            detalle={"motivo": "API de estado de vuelo no disponible o cuota agotada"},
        )
        logger.warning("API de estado de vuelo no disponible — degradación ordenada (RNF-DIS-001)")
        return resumen

    vuelos = await _vuelos_candidatos(ventana_horas)
    for vuelo in vuelos:
        resumen["consultados"] += 1
        try:
            resultado = await client.consultar_estado(vuelo["numero_vuelo"], vuelo["fecha_salida"][:10])
        except Exception:
            # RNF-DIS-001: una falla puntual en ESTE vuelo no interrumpe el
            # resto del ciclo — se registra y se sigue con los demás.
            resumen["degradado"] = True
            await AuditService().insertar(
                "degradacion_api_estado_vuelo",
                "disrupciones",
                registro_id=vuelo["id"],
                detalle={"motivo": "Falla puntual al consultar la API real", "numero_vuelo": vuelo["numero_vuelo"]},
            )
            logger.warning("Falla al consultar estado real de %s", vuelo["numero_vuelo"], exc_info=True)
            continue

        if resultado is None:
            continue

        estado_api = resultado["estado_api"]
        tipo_cambio = _TIPO_CAMBIO_POR_ESTADO.get(estado_api)
        if tipo_cambio is None or estado_api == vuelo["estado"]:
            continue

        ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
        disrupcion = await repo.crear_disrupcion(
            {
                "vuelo_id": vuelo["id"],
                "fuente_deteccion": "api_real",
                "tipo_cambio": tipo_cambio,
                "estado": "activa",
                "detalle": (
                    f"Estado real ({estado_api}) distinto al registrado ({vuelo['estado']})"
                    + (f"; retraso {resultado['retraso_minutos']} min" if resultado.get("retraso_minutos") else "")
                ),
                "fecha_deteccion": ahora_iso,
            }
        )
        resumen["disrupciones_creadas"] += 1

        await actualizar_estado(vuelo["id"], estado_api, origen="automatico")
        await AuditService().insertar(
            "disrupcion_detectada",
            "disrupciones",
            registro_id=disrupcion["id"],
            detalle={"fuente_deteccion": "api_real", "tipo_cambio": tipo_cambio, "vuelo_id": vuelo["id"]},
        )

        # REG-E1: ninguna disrupción detectada queda sin su intento de notificación.
        await procesar_disrupcion(disrupcion["id"], sender)

    return resumen
