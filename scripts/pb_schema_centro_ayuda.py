"""Crea (idempotente) las 3 colecciones del módulo Centro de Ayuda
(CU-O97-100, T28, T36, NUEVO) en pocketbase-travel: `articulos_ayuda`,
`articulo_calificaciones`, `casos_escalados`.

CU-O100/T36: escalación vía email real (Gmail API, uso constante) —
`gmail_thread_id` es un soft-ref al hilo real, no una relation de PocketBase.

Ejecutar: python scripts/pb_schema_centro_ayuda.py
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def existing_collections(headers: dict) -> dict[str, dict]:
    resp = httpx.get(f"{PB_URL}/api/collections", params={"perPage": 200}, headers=headers, timeout=10)
    resp.raise_for_status()
    return {c["name"]: c for c in resp.json()["items"]}


def ensure_collection(headers: dict, payload: dict, cache: dict[str, dict]) -> dict:
    name = payload["name"]
    if name in cache:
        print(f"  = {name} ya existe, se omite")
        return cache[name]
    resp = httpx.post(f"{PB_URL}/api/collections", json=payload, headers=headers, timeout=10)
    if resp.status_code >= 400:
        print(f"  ! error creando {name}: {resp.status_code} {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    created = resp.json()
    cache[name] = created
    print(f"  + {name} creada (id={created['id']})")
    return created


def text_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "text", "required": required, "options": {}}


def bool_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "bool", "required": required, "options": {}}


def date_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "date", "required": required, "options": {}}


def select_field(name: str, values: list[str], required: bool = False) -> dict:
    return {"name": name, "type": "select", "required": required, "options": {"maxSelect": 1, "values": values}}


def relation_field(name: str, target_collection_id: str, required: bool = False) -> dict:
    return {
        "name": name,
        "type": "relation",
        "required": required,
        "options": {"collectionId": target_collection_id, "cascadeDelete": False, "maxSelect": 1},
    }


LOCKED_RULES = {
    "listRule": None,
    "viewRule": None,
    "createRule": None,
    "updateRule": None,
    "deleteRule": None,
}


def main() -> None:
    headers = {"Authorization": admin_token()}
    cache = existing_collections(headers)

    for dep in ("usuarios", "pasajeros"):
        if dep not in cache:
            print(f"! falta la colección '{dep}' — no se puede continuar", file=sys.stderr)
            sys.exit(1)

    print("Verificando/creando colecciones de Centro de Ayuda...")

    articulos_ayuda = ensure_collection(
        headers,
        {
            "name": "articulos_ayuda",
            "type": "base",
            "schema": [
                text_field("categoria", required=True),
                text_field("titulo", required=True),
                text_field("contenido", required=True),
                relation_field("autor_id", cache["usuarios"]["id"], required=True),
                bool_field("activo"),
                date_field("fecha_publicacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "articulo_calificaciones",
            "type": "base",
            "schema": [
                relation_field("articulo_id", articulos_ayuda["id"], required=True),
                relation_field("pasajero_id", cache["pasajeros"]["id"]),
                select_field("util", ["arriba", "abajo"], required=True),
                date_field("fecha", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "casos_escalados",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", cache["pasajeros"]["id"], required=True),
                text_field("asunto", required=True),
                text_field("mensaje", required=True),
                text_field("gmail_thread_id"),
                select_field("estado", ["abierto", "en_proceso", "resuelto"], required=True),
                relation_field("agente_asignado_id", cache["usuarios"]["id"]),
                date_field("fecha_creacion", required=True),
                date_field("fecha_resolucion"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
