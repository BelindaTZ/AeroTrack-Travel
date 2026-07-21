"""Endpoints internos de Disrupciones — sin input de un actor humano
directo, disparados por scheduler (Airflow). Misma nota de seguridad que
`app/reservas/router_interno.py`: en un despliegue real deben protegerse a
nivel de red o con token compartido; no implementado en esta sesión.
"""

from fastapi import APIRouter, Form, HTTPException

from app.disrupciones.integrations.flight_status_client import AviationStackClient
from app.disrupciones.integrations.gmail_client import GmailClientImpl
from app.disrupciones.integrations.notification_sender import GmailNotificationSender
from app.disrupciones.services.api_estado_vuelo_service import consultar_estados_cercanos
from app.disrupciones.services.monitor_correo_service import monitorear_correo
from app.disrupciones.services.notificacion_service import DisrupcionNoEncontrada, procesar_disrupcion
from app.disrupciones.services.reintento_service import NotificacionNoEncontrada, reintentar_notificacion

router = APIRouter(prefix="/internal/disrupciones")
router_notificaciones = APIRouter(prefix="/internal/notificaciones")


@router.post("/consultar-api")
async def consultar_api_endpoint() -> dict:
    return await consultar_estados_cercanos(AviationStackClient(), GmailNotificationSender())


@router.post("/monitorear-correo")
async def monitorear_correo_endpoint() -> dict:
    return await monitorear_correo(GmailClientImpl(), GmailNotificationSender())


@router_notificaciones.post("/enviar")
async def enviar_endpoint(disrupcion_id: str = Form(...)) -> dict:
    try:
        return await procesar_disrupcion(disrupcion_id, GmailNotificationSender())
    except DisrupcionNoEncontrada:
        raise HTTPException(status_code=404, detail="Disrupción no encontrada")


@router_notificaciones.post("/{notificacion_id}/reintentar")
async def reintentar_endpoint(notificacion_id: str) -> dict:
    try:
        return await reintentar_notificacion(notificacion_id, GmailNotificationSender())
    except NotificacionNoEncontrada:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
