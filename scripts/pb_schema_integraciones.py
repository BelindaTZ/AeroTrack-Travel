"""Crea (idempotente) las 2 colecciones propias del módulo Integraciones en
pocketbase-travel: `fuentes_datos_externas` (config + gobierno de cada
proveedor externo/regla interna) y `sincronizaciones_log` (bitácora de cada
corrida de sync, generaliza CU-T07 a las 5 fuentes catalogo_periodico).

Primer módulo migrado del esquema propuesto v3 (docs/aerotrack-travel-
propuesta-tablas-v3.dbml) — se eligió empezar por este porque varias
colecciones nuevas de otros módulos (Hoteles, Autos, Actividades, Cruceros)
van a referenciar `fuentes_datos_externas` una vez se implementen sus syncs.

Mismo patrón que scripts/pb_schema_seguridad.py: LOCKED_RULES (solo admin de
PocketBase; RBAC de aplicación se resuelve en rbac_service, no aquí),
credenciales desde .env (REG-B3), sin datos hardcodeados.

Ejecutar: python scripts/pb_schema_integraciones.py
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


def bool_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "bool", "required": required, "options": {}}


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


def number_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "number", "required": required, "options": {}}


def date_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "date", "required": required, "options": {}}


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
    print("Verificando/creando colecciones de Integraciones...")

    fuentes = ensure_collection(
        headers,
        {
            "name": "fuentes_datos_externas",
            "type": "base",
            "schema": [
                text_field("nombre", required=True, unique=True),
                select_field(
                    "tipo_uso",
                    ["constante", "catalogo_periodico", "cache_bajo_demanda", "regla_negocio_interna"],
                    required=True,
                ),
                text_field("host_env_var"),
                select_field("tipo_producto_alimentado", TIPOS_PRODUCTO),
                number_field("frecuencia_sincronizacion_horas"),
                bool_field("activa"),
                text_field("notas"),
                date_field("ultima_sincronizacion_exitosa"),
                text_field("modificado_por", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "sincronizaciones_log",
            "type": "base",
            "schema": [
                relation_field("fuente_id", fuentes["id"], required=True),
                select_field("tipo_producto", TIPOS_PRODUCTO, required=True),
                date_field("fecha_inicio", required=True),
                date_field("fecha_fin"),
                select_field("estado", ["exitoso", "fallido", "parcial"], required=True),
                number_field("registros_procesados"),
                number_field("registros_nuevos"),
                number_field("registros_actualizados"),
                number_field("unidades_cuota_consumidas"),
                text_field("error_detalle"),
                text_field("ejecutado_por"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
