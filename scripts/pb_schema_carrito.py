"""Crea (idempotente) las 2 colecciones del módulo Carrito (CU-O93-96,
NUEVO) en pocketbase-travel: `carritos` y `carrito_items`.

Deliberadamente separado de `reservas` (no reutiliza estado
pendiente_pago): un carrito no es un PNR, no bloquea cupo, y su ciclo de
vida (activo -> convertido | abandonado) es lo que necesitan CU-T26/T27
para medir recuperación de carritos abandonados. `carrito_items` usa el
mismo patrón polimórfico que `reserva_items` a propósito, para que
convertir carrito -> reserva (CU-O96) sea un mapeo 1:1 campo a campo.

Ejecutar: python scripts/pb_schema_carrito.py
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


def number_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "number", "required": required, "options": {}}


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

TIPOS_PRODUCTO = ["vuelo", "hotel", "auto", "actividad", "crucero"]


def producto_fields() -> list[dict]:
    return [
        text_field("vuelo_id"),
        text_field("tarifa_vuelo_id"),
        text_field("hotel_id"),
        text_field("hotel_tarifa_id"),
        text_field("auto_id"),
        text_field("actividad_id"),
        text_field("actividad_horario_id"),
        text_field("crucero_id"),
        text_field("crucero_camarote_id"),
    ]


def main() -> None:
    headers = {"Authorization": admin_token()}
    cache = existing_collections(headers)

    if "pasajeros" not in cache:
        print("! falta la colección 'pasajeros' — no se puede continuar", file=sys.stderr)
        sys.exit(1)

    print("Verificando/creando colecciones de Carrito...")

    carritos = ensure_collection(
        headers,
        {
            "name": "carritos",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", cache["pasajeros"]["id"], required=True),
                select_field("estado", ["activo", "convertido", "abandonado"], required=True),
                date_field("fecha_creacion", required=True),
                date_field("fecha_ultima_actividad", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "carrito_items",
            "type": "base",
            "schema": [
                relation_field("carrito_id", carritos["id"], required=True),
                select_field("tipo_producto", TIPOS_PRODUCTO, required=True),
                *producto_fields(),
                number_field("precio_snapshot", required=True),
                date_field("fecha_agregado", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
