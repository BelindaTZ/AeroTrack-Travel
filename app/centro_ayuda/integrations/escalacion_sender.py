"""RF-AYU-004 (CU-O100) — única puerta al envío real del email de
escalación (REG-I6/B3). Reutiliza las mismas credenciales OAuth de Gmail
que Disrupciones (`gmail_api.*` en `configuracion_sistema`), pero es una
implementación propia — no importa `app.disrupciones` — porque este
módulo necesita el `threadId` real de vuelta para `casos_escalados.
gmail_thread_id`; `NotificationSender.enviar()` de Disrupciones solo
devuelve `bool`, no expone eso (mismo criterio de "única puerta por
módulo" que ya separa `gmail_client.py`/`notification_sender.py` ahí).

No hay una casilla de "equipo de soporte" separada — `gmail_api.
monitored_email` (la misma cuenta que Disrupciones ya monitorea) hace de
bandeja compartida: el caso se envía DE esa cuenta A esa misma cuenta,
con `Reply-To` al pasajero para que un Agente pueda responderle
directamente desde Gmail sin salir del hilo."""

import abc
import base64
from email.mime.text import MIMEText

import httpx

from app.shared.pocketbase_client import get_pocketbase_client

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class EscalacionSender(abc.ABC):
    @abc.abstractmethod
    async def enviar(self, email_pasajero: str, asunto: str, cuerpo: str) -> str | None:
        """Retorna el `threadId` real de Gmail si el envío fue exitoso,
        `None` si el proveedor confirmó una falla real (nunca lanza para
        un fallo de negocio esperado)."""


class GmailEscalacionSender(EscalacionSender):
    async def _config(self) -> dict:
        client = get_pocketbase_client()
        claves = [
            "gmail_api.client_id", "gmail_api.client_secret", "gmail_api.refresh_token",
            "gmail_api.monitored_email",
        ]
        valores = {}
        for clave in claves:
            registro = await client.get_first("configuracion_sistema", f'clave="{clave}"')
            if registro is None:
                raise RuntimeError(f"configuracion_sistema.{clave} no está sembrado")
            valores[clave] = registro["valor"]
        return valores

    async def _access_token(self, config: dict) -> str:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "client_id": config["gmail_api.client_id"],
                    "client_secret": config["gmail_api.client_secret"],
                    "refresh_token": config["gmail_api.refresh_token"],
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def enviar(self, email_pasajero: str, asunto: str, cuerpo: str) -> str | None:
        config = await self._config()
        token = await self._access_token(config)
        bandeja = config["gmail_api.monitored_email"]

        mensaje = MIMEText(cuerpo)
        mensaje["to"] = bandeja
        mensaje["from"] = bandeja
        mensaje["reply-to"] = email_pasajero
        mensaje["subject"] = f"[Caso escalado] {asunto}"
        raw = base64.urlsafe_b64encode(mensaje.as_bytes()).decode("ascii")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                _GMAIL_SEND_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"raw": raw},
            )
        if resp.status_code >= 300:
            return None
        return resp.json().get("threadId")
