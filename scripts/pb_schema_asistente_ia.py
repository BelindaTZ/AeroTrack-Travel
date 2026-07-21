"""Crea (idempotente) las 2 colecciones del módulo Asistente IA
(CU-O106-111, NUEVO) en pocketbase-travel: `conversaciones_ia`,
`mensajes_ia`. Usa Groq/Gemini (uso constante, no catálogo periódico) —
sin colección de catálogo propia.

Ejecutar: python scripts/pb_schema_asistente_ia.py
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

    if "pasajeros" not in cache:
        print("! falta la colección 'pasajeros' — no se puede continuar", file=sys.stderr)
        sys.exit(1)

    print("Verificando/creando colecciones de Asistente IA...")

    conversaciones_ia = ensure_collection(
        headers,
        {
            "name": "conversaciones_ia",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", cache["pasajeros"]["id"], required=True),
                text_field("titulo"),
                date_field("fecha_inicio", required=True),
                date_field("fecha_ultima_actividad", required=True),
                bool_field("activa"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "mensajes_ia",
            "type": "base",
            "schema": [
                relation_field("conversacion_id", conversaciones_ia["id"], required=True),
                select_field("rol", ["usuario", "asistente"], required=True),
                text_field("contenido", required=True),
                select_field("calificacion", ["arriba", "abajo"]),
                date_field("fecha", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
