"""Crea (idempotente) `tipos_paquete_descuento` (módulo Paquetes, NUEVO,
CU-O76-80/CU-T14). Paquetes no tiene catálogo propio — un paquete ES una
reserva con ≥2 tipos de producto en `reserva_items` (`reservas.es_paquete`);
lo único nuevo aquí es la configuración de descuento por combinación.

`combinacion` es texto libre controlado por la UI de administración, no
enum cerrado, para no migrar esquema cada vez que se agregue una
combinación nueva (ej. "vuelo+hotel", "vuelo+hotel+auto").

Ejecutar: python scripts/pb_schema_paquetes.py
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


def text_field(name: str, required: bool = False, unique: bool = False) -> dict:
    return {"name": name, "type": "text", "required": required, "unique": unique, "options": {}}


def number_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "number", "required": required, "options": {}}


def bool_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "bool", "required": required, "options": {}}


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
    print("Verificando/creando tipos_paquete_descuento...")

    ensure_collection(
        headers,
        {
            "name": "tipos_paquete_descuento",
            "type": "base",
            "schema": [
                text_field("combinacion", required=True, unique=True),
                number_field("porcentaje_descuento", required=True),
                bool_field("activo"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
