"""RF-DIS-002 (CU-O28) — única puerta a la Gmail API (OAuth, REG-I6/B3).

Interfaz abstracta + implementación real vía REST directo (sin el SDK
`google-api-python-client` — httpx alcanza para los 2 endpoints que se
necesitan y evita una dependencia pesada, mismo criterio que
`pocketbase_client.py`).
"""

import abc
import base64
import datetime

import httpx

from app.shared.pocketbase_client import get_pocketbase_client

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailClient(abc.ABC):
    @abc.abstractmethod
    async def leer_correos_nuevos(self, ultimas_horas: int = 24) -> list[dict]:
        """Retorna `[{"asunto", "remitente", "cuerpo_texto", "fecha"}, ...]`."""


def _extraer_texto_plano(payload: dict) -> str:
    """Recorre las partes MIME buscando `text/plain`; si no hay body
    decodificable, el snippet (siempre presente) es un fallback razonable."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _decodificar_b64url(payload["body"]["data"])
    for parte in payload.get("parts", []) or []:
        texto = _extraer_texto_plano(parte)
        if texto:
            return texto
    return ""


def _decodificar_b64url(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


class GmailClientImpl(GmailClient):
    async def _config(self) -> dict:
        client = get_pocketbase_client()
        claves = ["gmail_api.client_id", "gmail_api.client_secret", "gmail_api.refresh_token"]
        valores = {}
        for clave in claves:
            registro = await client.get_first("configuracion_sistema", f'clave="{clave}"')
            if registro is None:
                raise RuntimeError(f"configuracion_sistema.{clave} no está sembrado")
            valores[clave] = registro["valor"]
        return valores

    async def _access_token(self) -> str:
        config = await self._config()
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

    async def leer_correos_nuevos(self, ultimas_horas: int = 24) -> list[dict]:
        token = await self._access_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            resp = await client.get(
                f"{_GMAIL_API}/messages",
                params={"q": f"newer_than:{ultimas_horas}h", "maxResults": 25},
            )
            resp.raise_for_status()
            ids = [m["id"] for m in resp.json().get("messages", [])]

            correos = []
            for msg_id in ids:
                detalle = await client.get(f"{_GMAIL_API}/messages/{msg_id}", params={"format": "full"})
                detalle.raise_for_status()
                data = detalle.json()
                headers_msg = {h["name"]: h["value"] for h in data["payload"].get("headers", [])}
                cuerpo = _extraer_texto_plano(data["payload"]) or data.get("snippet", "")
                fecha_ms = int(data.get("internalDate", "0"))
                fecha = datetime.datetime.fromtimestamp(
                    fecha_ms / 1000, tz=datetime.timezone.utc
                ).isoformat()
                correos.append(
                    {
                        "asunto": headers_msg.get("Subject", ""),
                        "remitente": headers_msg.get("From", ""),
                        "cuerpo_texto": cuerpo,
                        "fecha": fecha,
                    }
                )
            return correos
