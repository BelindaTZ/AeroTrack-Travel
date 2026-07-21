"""Crea (idempotente) las 5 colecciones del módulo Cuenta/Mis Viajes
(CU-O87-92, NUEVO) en pocketbase-travel: `favoritos`, `busquedas_recientes`,
`viajes_personalizados`, `programa_beneficios_niveles`,
`programa_beneficios_movimientos`.

CU-O87 ("Ver Mis Viajes") no tiene tabla propia — es una vista sobre
`reservas`+`reserva_items` filtrada por `pasajero_titular_id`.

Ejecutar: python scripts/pb_schema_cuenta_mis_viajes.py
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


def json_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "json", "required": required, "options": {"maxSize": 2000000}}


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


def main() -> None:
    headers = {"Authorization": admin_token()}
    cache = existing_collections(headers)

    for dep in ("pasajeros", "reservas"):
        if dep not in cache:
            print(f"! falta la colección '{dep}' — no se puede continuar", file=sys.stderr)
            sys.exit(1)

    print("Verificando/creando colecciones de Cuenta/Mis Viajes...")

    ensure_collection(
        headers,
        {
            "name": "favoritos",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", cache["pasajeros"]["id"], required=True),
                select_field("tipo", ["destino", "hotel", "actividad"], required=True),
                text_field("producto_ref", required=True),
                date_field("fecha_guardado", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "busquedas_recientes",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", cache["pasajeros"]["id"], required=True),
                select_field("tipo_producto", TIPOS_PRODUCTO, required=True),
                json_field("criterios", required=True),
                date_field("fecha", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "viajes_personalizados",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", cache["pasajeros"]["id"], required=True),
                text_field("nombre", required=True),
                text_field("descripcion"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "programa_beneficios_niveles",
            "type": "base",
            "schema": [
                text_field("nombre_nivel", required=True),
                number_field("puntos_minimos", required=True),
                text_field("beneficios"),
                number_field("puntos_por_dolar", required=True),
                number_field("vencimiento_meses"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "programa_beneficios_movimientos",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", cache["pasajeros"]["id"], required=True),
                select_field("tipo", ["acumulacion", "redencion"], required=True),
                number_field("puntos", required=True),
                relation_field("reserva_id", cache["reservas"]["id"]),
                text_field("descripcion"),
                date_field("fecha", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
