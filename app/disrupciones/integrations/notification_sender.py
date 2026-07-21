"""RF-DIS-004/006 — única puerta al envío real de notificaciones (REG-F1).

`configuracion_sistema.smtp.host` quedó sembrado como placeholder sin
contraseña real — no hay credencial SMTP utilizable. La única credencial de
envío real disponible es el OAuth de Gmail (`gmail_api.*`, ya usado para
leer correo en `gmail_client.py`) — la Gmail API también sirve para
*enviar* (`users.messages.send`) con el mismo token, así que el envío real
de canal "email" reutiliza esas credenciales en vez de inventar una vía
SMTP sin secreto configurado. SMS no tiene ningún proveedor sembrado —
`enviar()` lo rechaza explícitamente en vez de simular un envío que nunca
saldría de verdad.
"""

import abc
import base64
from email.mime.text import MIMEText

import httpx

from app.shared.pocketbase_client import get_pocketbase_client

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class CanalNoDisponible(Exception):
    pass


class NotificationSender(abc.ABC):
    @abc.abstractmethod
    async def enviar(self, canal: str, destino: str, asunto: str, cuerpo: str) -> bool:
        """Retorna `True` si el proveedor confirmó el envío; `False` si el
        proveedor respondió con una falla real (nunca lanza para un fallo
        de negocio esperado — el llamador decide qué hacer con `False`)."""


class GmailNotificationSender(NotificationSender):
    async def _config(self) -> dict:
        client = get_pocketbase_client()
        claves = ["gmail_api.client_id", "gmail_api.client_secret", "gmail_api.refresh_token", "smtp.remitente"]
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

    async def enviar(self, canal: str, destino: str, asunto: str, cuerpo: str) -> bool:
        if canal != "email":
            raise CanalNoDisponible(f"Sin proveedor real configurado para el canal '{canal}'")

        config = await self._config()
        token = await self._access_token(config)

        mensaje = MIMEText(cuerpo)
        mensaje["to"] = destino
        mensaje["from"] = config["smtp.remitente"]
        mensaje["subject"] = asunto
        raw = base64.urlsafe_b64encode(mensaje.as_bytes()).decode("ascii")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                _GMAIL_SEND_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"raw": raw},
            )
        return resp.status_code < 300
