"""Crea (idempotente) las 5 colecciones del módulo Ofertas y Promociones
(CU-O101-105, NUEVO) en pocketbase-travel: `ofertas_destacadas`,
`cupones_descuento`, `cupones_uso`, `newsletter_suscripciones`,
`campanas_email`.

`cupones_descuento.acumulable_con_paquete` (CU-T44, resuelve QP-18):
nullable = hereda el default global (configuracion_sistema clave
"cupones.acumulable_con_paquete_default"); true/false = excepción explícita
para ESE cupón, con prioridad sobre el default global. Solo se evalúa
cuando reservas.es_paquete = true.

Ejecutar: python scripts/pb_schema_ofertas_promociones.py
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

    for dep in ("pasajeros", "reservas", "usuarios"):
        if dep not in cache:
            print(f"! falta la colección '{dep}' — no se puede continuar", file=sys.stderr)
            sys.exit(1)

    print("Verificando/creando colecciones de Ofertas y Promociones...")

    ensure_collection(
        headers,
        {
            "name": "ofertas_destacadas",
            "type": "base",
            "schema": [
                select_field("tipo_producto", TIPOS_PRODUCTO, required=True),
                text_field("producto_ref", required=True),
                text_field("titulo", required=True),
                text_field("descripcion"),
                text_field("imagen"),
                date_field("fecha_inicio", required=True),
                date_field("fecha_fin", required=True),
                bool_field("activa"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    cupones_descuento = ensure_collection(
        headers,
        {
            "name": "cupones_descuento",
            "type": "base",
            "schema": [
                text_field("codigo", required=True, unique=True),
                select_field("tipo", ["monto_fijo", "porcentaje"], required=True),
                number_field("valor", required=True),
                select_field("producto_aplicable", TIPOS_PRODUCTO),
                date_field("fecha_expiracion", required=True),
                number_field("usos_maximos"),
                number_field("usos_actuales"),
                bool_field("activo"),
                bool_field("acumulable_con_paquete"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "cupones_uso",
            "type": "base",
            "schema": [
                relation_field("cupon_id", cupones_descuento["id"], required=True),
                relation_field("reserva_id", cache["reservas"]["id"], required=True),
                date_field("fecha_uso", required=True),
                number_field("monto_descontado", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "newsletter_suscripciones",
            "type": "base",
            "schema": [
                relation_field("pasajero_id", cache["pasajeros"]["id"]),
                text_field("email", required=True),
                date_field("fecha_suscripcion", required=True),
                bool_field("activo"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "campanas_email",
            "type": "base",
            "schema": [
                text_field("nombre", required=True),
                json_field("segmento_criterio", required=True),
                text_field("plantilla", required=True),
                date_field("fecha_envio"),
                select_field("estado", ["borrador", "programada", "enviada"]),
                relation_field("creado_por", cache["usuarios"]["id"], required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
