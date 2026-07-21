"""Crea (idempotente) las 4 colecciones del módulo Hoteles (CU-O54-60,
NUEVO) en pocketbase-travel: `hoteles_catalogo`, `hoteles_tarifas`,
`hoteles_resenas`, `cargos_locales_destino`.

Fuente elegida para el catálogo: HotelLens (Google Hotels) — ver nota
completa en docs/aerotrack-travel-propuesta-tablas-v3.dbml línea ~786.
`cargos_locales_destino` es la única tabla de esta vertical con datos reales
desde el día uno sin depender de ninguna API: importación manual de
`fuentes_extra/holidu_tourist_tax_por_ciudad.csv` (100 ciudades, snapshot de
Holidu) — por eso NO se referencia en `fuentes_datos_externas`.

Ejecutar: python scripts/pb_schema_hoteles.py
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


def main() -> None:
    headers = {"Authorization": admin_token()}
    cache = existing_collections(headers)

    for dep in ("proveedores_comerciales", "politicas_reembolso"):
        if dep not in cache:
            print(f"! falta la colección '{dep}' — no se puede continuar", file=sys.stderr)
            sys.exit(1)

    print("Verificando/creando colecciones de Hoteles...")

    hoteles_catalogo = ensure_collection(
        headers,
        {
            "name": "hoteles_catalogo",
            "type": "base",
            "schema": [
                text_field("nombre", required=True),
                text_field("direccion", required=True),
                text_field("ciudad", required=True),
                text_field("pais", required=True),
                number_field("latitud"),
                number_field("longitud"),
                number_field("estrellas"),
                number_field("calificacion_promedio"),
                number_field("cantidad_resenas"),
                json_field("category_scores"),
                text_field("descripcion_corta"),
                text_field("descripcion"),
                json_field("servicios"),
                text_field("hora_checkin"),
                text_field("hora_checkout"),
                text_field("imagen_principal"),
                relation_field("proveedor_comercial_id", cache["proveedores_comerciales"]["id"]),
                text_field("fuente_entity_url"),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "hoteles_tarifas",
            "type": "base",
            "schema": [
                relation_field("hotel_id", hoteles_catalogo["id"], required=True),
                text_field("tipo_habitacion", required=True),
                text_field("bed_type"),
                number_field("max_ocupantes"),
                number_field("tamano_m2"),
                bool_field("desayuno_incluido"),
                number_field("precio_final", required=True),
                text_field("moneda", required=True),
                bool_field("reembolsable", required=True),
                date_field("cancelacion_hasta"),
                relation_field("politica_reembolso_id", cache["politicas_reembolso"]["id"]),
                number_field("cupos_disponibles"),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "hoteles_resenas",
            "type": "base",
            "schema": [
                relation_field("hotel_id", hoteles_catalogo["id"], required=True),
                text_field("autor"),
                number_field("calificacion"),
                number_field("escala_calificacion"),
                text_field("comentario"),
                text_field("fecha_relativa_texto"),
                text_field("fuente"),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "cargos_locales_destino",
            "type": "base",
            "schema": [
                text_field("ciudad", required=True),
                text_field("pais", required=True),
                text_field("tipo_cargo", required=True),
                text_field("regla_texto", required=True),
                select_field("tipo_valor_estimado", ["monto_fijo", "porcentaje"]),
                number_field("monto_estimado"),
                number_field("porcentaje_estimado"),
                text_field("fuente"),
                bool_field("activo"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
