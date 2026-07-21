"""Agrega (idempotente) el campo `cantidad` a `carrito_items` y
`reserva_items` — necesario para validar cupo real por N unidades
(participantes de una actividad, camarotes de un crucero, etc.) en vez de
asumir siempre 1. Antes de esto, Actividades calculaba
`precio_snapshot = precio_unitario * participantes` sin registrar la
cantidad en ningún lado, lo que además rompía la revalidación de precio
de Carrito (comparaba el total contra el precio unitario vigente).

`required=false`, default de negocio 1 (aplicado en código, no en
esquema) — mismo criterio que el resto de campos numéricos nuevos desde
la corrección de `pb_schema_fix_required_numericos.py`.

Ejecutar: python scripts/pb_schema_fix_cantidad_items.py
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


def get_collection(headers: dict, name: str) -> dict:
    resp = httpx.get(f"{PB_URL}/api/collections/{name}", headers=headers, timeout=10)
    resp.raise_for_status()
    c = resp.json()
    c["schema"] = c.get("schema", c.get("fields"))
    return c


def ensure_field(headers: dict, collection: dict, campo: dict) -> None:
    existentes = {f["name"] for f in collection["schema"]}
    if campo["name"] in existentes:
        print(f"  = {collection['name']}.{campo['name']} ya existe, se omite")
        return
    schema_actualizado = collection["schema"] + [campo]
    resp = httpx.patch(
        f"{PB_URL}/api/collections/{collection['id']}",
        json={"schema": schema_actualizado},
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        print(f"  ! error agregando {campo['name']} a {collection['name']}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    print(f"  + {collection['name']}.{campo['name']} agregado")


def main() -> None:
    headers = {"Authorization": admin_token()}
    campo_cantidad = {"name": "cantidad", "type": "number", "required": False, "options": {}}

    for nombre in ("carrito_items", "reserva_items"):
        print(f"Verificando {nombre}...")
        coleccion = get_collection(headers, nombre)
        ensure_field(headers, coleccion, campo_cantidad)

    print("Listo.")


if __name__ == "__main__":
    main()
