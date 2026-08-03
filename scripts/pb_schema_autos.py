"""Crea (idempotente) `autos_catalogo` (módulo Autos, NUEVO, CU-O61-64) en
pocketbase-travel. Ofertas point-in-time de Priceline/Booking/Expedia
(`proveedor_agregador`) — `fuente_oferta_ref` guarda el token real para
re-cotizar antes de confirmar, ya que estas APIs no honran fecha/ubicación
solicitada de forma fija.

Ejecutar: python scripts/pb_schema_autos.py
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


def main() -> None:
    headers = {"Authorization": admin_token()}
    cache = existing_collections(headers)

    for dep in ("proveedores_comerciales", "politicas_reembolso"):
        if dep not in cache:
            print(f"! falta la colección '{dep}' — no se puede continuar", file=sys.stderr)
            sys.exit(1)

    print("Verificando/creando autos_catalogo...")

    autos_catalogo = ensure_collection(
        headers,
        {
            "name": "autos_catalogo",
            "type": "base",
            "schema": [
                text_field("proveedor_agregador", required=True),
                relation_field("proveedor_comercial_id", cache["proveedores_comerciales"]["id"]),
                text_field("marca"),
                text_field("modelo"),
                text_field("categoria"),
                text_field("transmision"),
                text_field("ciudad_recogida", required=True),
                text_field("aeropuerto_codigo"),
                number_field("precio_dia", required=True),
                text_field("moneda", required=True),
                select_field("modalidad_pago_disponible", ["pagar_ahora", "pagar_al_recoger"]),
                relation_field("politica_reembolso_id", cache["politicas_reembolso"]["id"]),
                text_field("fuente_oferta_ref"),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            # Disponibilidad real por DÍA — antes recogida/devolución eran
            # cosméticas (ver errores-conocidos.md). `autos_catalogo` se borra
            # y recrea entero con IDs nuevos en cada refresh
            # (`eliminar_ofertas_de_ciudad`) — estas filas se limpian junto
            # con el auto al que pertenecen.
            "name": "autos_disponibilidad",
            "type": "base",
            "schema": [
                relation_field("auto_id", autos_catalogo["id"], required=True),
                date_field("fecha", required=True),
                number_field("cupos_disponibles"),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
