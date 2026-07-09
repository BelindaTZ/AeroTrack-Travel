"""
AeroTrack Travel — Cliente mínimo de PocketBase para los DAGs
================================================================
Envoltorio delgado sobre requests: autentica como admin de
pocketbase-travel y expone helpers CRUD usados por las tareas de
los DAGs (generación de catálogo, simulador de disrupciones).

No se usa un SDK porque el volumen de llamadas por corrida es bajo
(decenas, no miles de registros) — mismo criterio que el proyecto
anterior, que solo usa requests + minio directamente en dags/.
"""

from __future__ import annotations

import requests

import config

_token_cache: dict[str, str] = {}


def _token() -> str:
    if "token" not in _token_cache:
        resp = requests.post(
            f"{config.PB_TRAVEL_URL}/api/admins/auth-with-password",
            json={"identity": config.PB_TRAVEL_EMAIL, "password": config.PB_TRAVEL_PASSWORD},
            timeout=15,
        )
        resp.raise_for_status()
        _token_cache["token"] = resp.json()["token"]
    return _token_cache["token"]


def _headers() -> dict:
    return {"Authorization": _token()}


def list_all(collection: str, filter_: str | None = None) -> list[dict]:
    """Trae todos los registros de una colección (pagina automáticamente)."""
    items: list[dict] = []
    page = 1
    while True:
        params = {"page": page, "perPage": 200}
        if filter_:
            params["filter"] = filter_
        resp = requests.get(
            f"{config.PB_TRAVEL_URL}/api/collections/{collection}/records",
            headers=_headers(), params=params, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get("items", []))
        if page >= data.get("totalPages", 1):
            break
        page += 1
    return items


def get_first(collection: str, filter_: str):
    items = list_all(collection, filter_)
    return items[0] if items else None


def create(collection: str, data: dict) -> dict:
    resp = requests.post(
        f"{config.PB_TRAVEL_URL}/api/collections/{collection}/records",
        headers=_headers(), json=data, timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Error creando en {collection}: {resp.status_code} {resp.text}")
    return resp.json()


def update(collection: str, record_id: str, data: dict) -> dict:
    resp = requests.patch(
        f"{config.PB_TRAVEL_URL}/api/collections/{collection}/records/{record_id}",
        headers=_headers(), json=data, timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Error actualizando {collection}/{record_id}: {resp.status_code} {resp.text}")
    return resp.json()


def get_config(clave: str, default: str | None = None) -> str | None:
    """Lee un valor de configuracion_sistema (CU-O15..O22). Cae al default
    si la clave no existe todavía (p.ej. primera corrida antes del seed)."""
    rec = get_first("configuracion_sistema", f'clave="{clave}"')
    return rec["valor"] if rec else default
