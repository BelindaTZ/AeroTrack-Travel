"""Siembra idempotente de la política de reintentos de notificaciones
(RF-DIS-006/RNF-DIS-002) — `configuracion_sistema` no tenía estas dos claves
todavía (el resto de claves de Disrupciones ya estaban sembradas de una
sesión anterior: `disrupciones.*`, `api_estado_vuelo.*`, `gmail_api.*`).

Ejecutar: python scripts/seed_disrupciones_config.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

CLAVES = [
    {
        "clave": "notificaciones.max_reintentos",
        "valor": "3",
        "categoria": "canales_notificacion",
        "descripcion": "RF-DIS-006 — número máximo de reintentos de envío antes de marcar fallido_definitivo",
    },
    {
        "clave": "notificaciones.intervalo_reintento_minutos",
        "valor": "10",
        "categoria": "canales_notificacion",
        "descripcion": "RF-DIS-006 — minutos de espera mínimos entre reintentos de envío",
    },
]


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def main() -> None:
    headers = {"Authorization": admin_token()}

    resp = httpx.get(
        f"{PB_URL}/api/collections/usuarios/records",
        params={"filter": 'tipo_actor="administrador"', "perPage": 1},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json()["items"]
    if not items:
        raise RuntimeError("No hay ningún usuario administrador sembrado")
    admin_id = items[0]["id"]

    for entrada in CLAVES:
        existente = httpx.get(
            f"{PB_URL}/api/collections/configuracion_sistema/records",
            params={"filter": f'clave="{entrada["clave"]}"', "perPage": 1},
            headers=headers,
            timeout=10,
        )
        existente.raise_for_status()
        if existente.json()["items"]:
            print(f"= {entrada['clave']} ya existe")
            continue

        crear = httpx.post(
            f"{PB_URL}/api/collections/configuracion_sistema/records",
            json={**entrada, "modificado_por": admin_id},
            headers=headers,
            timeout=10,
        )
        crear.raise_for_status()
        print(f"+ {entrada['clave']} = {entrada['valor']}")


if __name__ == "__main__":
    main()
