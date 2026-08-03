"""RF-CAR-T01 — disparado por el scheduler (Airflow), sin input de usuario.
Mismo criterio de seguridad que `app/reservas/router_interno.py`: no exige
autenticación porque no hay un actor humano detrás."""

from fastapi import APIRouter

from app.carrito.services.abandono_service import marcar_abandonados_y_notificar
from app.disrupciones.integrations.notification_sender import GmailNotificationSender

router = APIRouter(prefix="/internal/carrito")


@router.post("/marcar-abandonados")
async def marcar_abandonados_endpoint() -> dict:
    cantidad = await marcar_abandonados_y_notificar(GmailNotificationSender())
    return {"marcados_abandonados": cantidad}
