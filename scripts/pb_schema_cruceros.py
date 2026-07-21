"""Crea (idempotente) las 4 colecciones del módulo Cruceros (CU-O71-75,
NUEVO) en pocketbase-travel: `navieras`, `barcos`, `cruceros_catalogo`,
`cruceros_camarotes_tarifa`.

Fuente: Cruise Pricing API (10/11 endpoints funcionales). Igual que
Actividades, `cupos_disponibles` en camarotes_tarifa es regla de negocio
interna (la API no expone inventario real) — required=False, mismo motivo
documentado en errores-conocidos.md para tarifas_vuelo.

Ejecutar: python scripts/pb_schema_cruceros.py
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


def date_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "date", "required": required, "options": {}}


def json_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "json", "required": required, "options": {"maxSize": 2000000}}


def file_field(name: str, mime_types: list[str], max_size: int = 5242880) -> dict:
    return {
        "name": name,
        "type": "file",
        "required": False,
        "options": {"maxSelect": 1, "maxSize": max_size, "mimeTypes": mime_types},
    }


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

    for dep in ("proveedores_comerciales", "politicas_reembolso"):
        if dep not in cache:
            print(f"! falta la colección '{dep}' — no se puede continuar", file=sys.stderr)
            sys.exit(1)

    print("Verificando/creando colecciones de Cruceros...")

    navieras = ensure_collection(
        headers,
        {
            "name": "navieras",
            "type": "base",
            "schema": [
                text_field("nombre", required=True),
                text_field("slug_proveedor", required=True, unique=True),
                json_field("destinos"),
                relation_field("proveedor_comercial_id", cache["proveedores_comerciales"]["id"]),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    barcos = ensure_collection(
        headers,
        {
            "name": "barcos",
            "type": "base",
            "schema": [
                relation_field("naviera_id", navieras["id"], required=True),
                text_field("nombre", required=True),
                json_field("servicios_abordo"),
                file_field("planos_cubierta", ["image/jpeg", "image/png", "image/webp", "application/pdf"]),
                text_field("politicas"),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    cruceros_catalogo = ensure_collection(
        headers,
        {
            "name": "cruceros_catalogo",
            "type": "base",
            "schema": [
                relation_field("naviera_id", navieras["id"], required=True),
                relation_field("barco_id", barcos["id"], required=True),
                text_field("fuente_cruise_id", required=True),
                date_field("fecha_zarpe", required=True),
                number_field("duracion_dias"),
                json_field("itinerario_puertos"),
                number_field("precio_base", required=True),
                text_field("moneda", required=True),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "cruceros_camarotes_tarifa",
            "type": "base",
            "schema": [
                relation_field("crucero_id", cruceros_catalogo["id"], required=True),
                text_field("tipo_camarote", required=True),
                number_field("precio_por_persona", required=True),
                number_field("cupos_disponibles"),
                relation_field("politica_reembolso_id", cache["politicas_reembolso"]["id"]),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
