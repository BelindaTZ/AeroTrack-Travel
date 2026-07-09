"""Corrige un defecto de esquema heredado (colección creada en una sesión
anterior, antes de este módulo): `tarifas_vuelo.cupos_disponibles` estaba
marcado `required=true`. PocketBase 0.22 valida "required" en campos
numéricos tratando 0 como valor ausente ("Missing required value"), lo cual
rompe por completo el caso legítimo de "cupo agotado" (RF-VUE-005) — un
campo obligatorio no puede representar su propio valor mínimo válido.

Idempotente: no falla si ya se corrigió.

Ejecutar: python scripts/pb_schema_vuelos_fix.py
"""

import os

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


def main() -> None:
    headers = {"Authorization": admin_token()}
    resp = httpx.get(f"{PB_URL}/api/collections/tarifas_vuelo", headers=headers, timeout=10)
    resp.raise_for_status()
    coleccion = resp.json()

    schema = coleccion["schema"]
    campo = next(f for f in schema if f["name"] == "cupos_disponibles")
    if not campo["required"]:
        print("= cupos_disponibles ya es required=false, nada que hacer")
        return

    campo["required"] = False
    patch = httpx.patch(
        f"{PB_URL}/api/collections/{coleccion['id']}",
        json={"schema": schema},
        headers=headers,
        timeout=10,
    )
    patch.raise_for_status()
    print("+ tarifas_vuelo.cupos_disponibles ahora es required=false (permite 0)")


if __name__ == "__main__":
    main()
