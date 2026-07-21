"""Crea (idempotente) las 3 colecciones del módulo Actividades (CU-O65-70,
NUEVO) en pocketbase-travel: `actividades_catalogo`, `actividades_horarios`,
`actividades_resenas`.

`actividades_horarios.cupos_disponibles` es regla de negocio interna, no
inventario real de proveedor (confirmado: ninguna API probada da
disponibilidad real) — mismo patrón que `tarifas_vuelo.cupos_disponibles`,
por eso required=False (evitar el bug ya documentado en errores-conocidos.md
donde un cupo=0 legítimo choca con required=true en PocketBase).

Ejecutar: python scripts/pb_schema_actividades.py
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

    print("Verificando/creando colecciones de Actividades...")

    actividades_catalogo = ensure_collection(
        headers,
        {
            "name": "actividades_catalogo",
            "type": "base",
            "schema": [
                text_field("nombre", required=True),
                text_field("ciudad", required=True),
                text_field("pais", required=True),
                text_field("categoria"),
                number_field("calificacion_promedio"),
                number_field("cantidad_resenas"),
                text_field("descripcion"),
                text_field("inclusiones"),
                text_field("punto_encuentro"),
                text_field("condiciones"),
                number_field("precio_desde"),
                text_field("moneda"),
                text_field("imagen_principal"),
                relation_field("proveedor_comercial_id", cache["proveedores_comerciales"]["id"]),
                relation_field("politica_reembolso_id", cache["politicas_reembolso"]["id"]),
                text_field("fuente_content_id"),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "actividades_horarios",
            "type": "base",
            "schema": [
                relation_field("actividad_id", actividades_catalogo["id"], required=True),
                date_field("fecha", required=True),
                text_field("hora"),
                number_field("cupos_disponibles"),
                number_field("precio", required=True),
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
            "name": "actividades_resenas",
            "type": "base",
            "schema": [
                relation_field("actividad_id", actividades_catalogo["id"], required=True),
                text_field("autor"),
                number_field("calificacion"),
                text_field("comentario"),
                date_field("fecha_resena"),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
