"""Crea (idempotente) las 2 colecciones nuevas del módulo Pasajeros en
pocketbase-travel: `documentos_viaje` (CU-O49, RF-PAS-005) y
`viajeros_frecuentes` (CU-O50, RF-PAS-006, "Gestionar viajeros frecuentes
guardados" — prellenar checkout con acompañantes recurrentes sin cuenta
propia).

Mismo patrón que scripts/pb_schema_seguridad.py: LOCKED_RULES, credenciales
desde .env (REG-B3).

Ejecutar: python scripts/pb_schema_pasajeros.py
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


def select_field(name: str, values: list[str], required: bool = False) -> dict:
    return {
        "name": name,
        "type": "select",
        "required": required,
        "options": {"maxSelect": 1, "values": values},
    }


def relation_field(name: str, target_collection_id: str, required: bool = False) -> dict:
    return {
        "name": name,
        "type": "relation",
        "required": required,
        "options": {"collectionId": target_collection_id, "cascadeDelete": False, "maxSelect": 1},
    }


def date_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "date", "required": required, "options": {}}


def file_field(name: str, mime_types: list[str], max_size: int = 5242880) -> dict:
    return {
        "name": name,
        "type": "file",
        "required": False,
        "options": {"maxSelect": 1, "maxSize": max_size, "mimeTypes": mime_types},
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
        print("! falta la colección 'pasajeros' (módulo Pasajeros Operativo) — no se puede continuar", file=sys.stderr)
        sys.exit(1)
    pasajeros = cache["pasajeros"]

    print("Verificando/creando colecciones de Pasajeros...")

    ensure_collection(
        headers,
        {
            "name": "documentos_viaje",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", pasajeros["id"], required=True),
                select_field("tipo", ["pasaporte", "cedula", "otro"], required=True),
                text_field("numero", required=True),
                text_field("pais_emision", required=True),
                date_field("fecha_vencimiento"),
                file_field("archivo", ["image/jpeg", "image/png", "image/webp", "application/pdf"]),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "viajeros_frecuentes",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", pasajeros["id"], required=True),
                text_field("nombre_completo", required=True),
                date_field("fecha_nacimiento"),
                text_field("numero_documento"),
                text_field("relacion"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
