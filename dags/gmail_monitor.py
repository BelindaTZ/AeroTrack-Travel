"""
AeroTrack Travel — Monitor de bandeja de correo de la agencia (CU-O41/O42)
=============================================================================
Principio F1: las credenciales OAuth se leen de configuracion_sistema
(gmail_api.*), nunca de .env directamente, para poder rotarlas desde la
UI (CU-O18) sin redeployar. Solo requests + REST directo a Gmail API,
sin el SDK de Google (mismo criterio de dependencias mínimas que el
resto de dags/: ver aerotrack_tasks.py del proyecto anterior).

Alcance de esta entrega: SOLO detección (CU-O41 monitorear, CU-O42
detectar cambio de itinerario). El envío de la notificación al pasajero
(CU-O43) queda fuera hasta que el canal de salida (SMTP, CU-O16) esté
implementado — ver disrupciones_tasks.py para el mismo criterio aplicado
al simulador estadístico.
"""

from __future__ import annotations

import time

import requests

import pocketbase_client as pb

_CATEGORIA = "gmail_api"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Heurística de palabras clave para CU-O42 (detectar cambio de itinerario)
# hasta que exista parsing estructurado por aerolínea.
PALABRAS_CLAVE_CAMBIO = [
    "flight change", "flight cancelled", "flight canceled", "itinerary change",
    "schedule change", "delayed", "cancellation", "gate change",
]


def _config(clave: str, default: str | None = None) -> str | None:
    return pb.get_config(f"{_CATEGORIA}.{clave}", default)


def _access_token() -> str:
    client_id = _config("client_id")
    client_secret = _config("client_secret")
    refresh_token = _config("refresh_token")
    if not (client_id and client_secret and refresh_token):
        raise RuntimeError("gmail_api.client_id/client_secret/refresh_token no están configurados")

    resp = requests.post(_TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"No se pudo refrescar el token OAuth de Gmail: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


def obtener_perfil() -> dict:
    """Confirma identidad y acceso: GET .../profile. Sirve como prueba de
    vida de la integración sin depender de que haya correos en la bandeja."""
    token = _access_token()
    resp = requests.get(f"{_API_BASE}/profile", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def listar_correos_recientes(query: str = "newer_than:7d", max_resultados: int = 20) -> list[dict]:
    """CU-O41: lista mensajes recientes de la bandeja monitoreada. `query`
    usa la sintaxis de búsqueda de Gmail (from:, subject:, newer_than:...)."""
    token = _access_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(f"{_API_BASE}/messages", headers=headers,
                         params={"q": query, "maxResults": max_resultados}, timeout=15)
    resp.raise_for_status()
    ids = [m["id"] for m in resp.json().get("messages", [])]

    mensajes = []
    for mid in ids:
        detalle = requests.get(f"{_API_BASE}/messages/{mid}", headers=headers,
                                params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                                timeout=15)
        detalle.raise_for_status()
        d = detalle.json()
        cabeceras = {h["name"]: h["value"] for h in d.get("payload", {}).get("headers", [])}
        mensajes.append({
            "id": mid,
            "asunto": cabeceras.get("Subject", ""),
            "de": cabeceras.get("From", ""),
            "fecha": cabeceras.get("Date", ""),
            "snippet": d.get("snippet", ""),
        })
        time.sleep(0.1)  # cortesía de rate-limit, F2
    return mensajes


def detectar_cambios_itinerario() -> list[dict]:
    """CU-O42: filtra los correos recientes por palabras clave de cambio
    de itinerario. Devuelve los que hicieron match (candidatos a generar
    una fila en disrupciones, fuente_deteccion='monitor_correo')."""
    mensajes = listar_correos_recientes()
    candidatos = []
    for m in mensajes:
        texto = f"{m['asunto']} {m['snippet']}".lower()
        if any(palabra in texto for palabra in PALABRAS_CLAVE_CAMBIO):
            candidatos.append(m)
    return candidatos
