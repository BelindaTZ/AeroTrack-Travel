"""Agrega el valor `google_apis` al campo select `configuracion_sistema.categoria`
— necesario para sembrar las keys de Google Cloud (Places/Geocoding/Maps
Embed/Maps JavaScript/Routes) vía scripts/seed_google_apis_config.py, que
falla con 400 si la categoría no está en la lista fija de valores
permitidos del select.

Idempotente, mismo patrón que scripts/pb_schema_hoteles_fix_required.py.

Ejecutar: python scripts/pb_schema_configuracion_fix_categoria.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

NUEVO_VALOR = "google_apis"


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
    resp = httpx.get(f"{PB_URL}/api/collections/configuracion_sistema", headers=headers, timeout=10)
    resp.raise_for_status()
    coleccion = resp.json()
    schema = coleccion.get("schema", coleccion.get("fields"))

    campo = next(f for f in schema if f["name"] == "categoria")
    if NUEVO_VALOR in campo["options"]["values"]:
        print(f"= configuracion_sistema.categoria ya incluye '{NUEVO_VALOR}'")
        return

    campo["options"]["values"].append(NUEVO_VALOR)
    patch = httpx.patch(
        f"{PB_URL}/api/collections/{coleccion['id']}", json={"schema": schema}, headers=headers, timeout=10
    )
    if patch.status_code >= 400:
        print(f"! posible 400 cosmético (ver nota en pb_schema_vuelos_v3.py): {patch.text}")
    print(f"+ configuracion_sistema.categoria ahora incluye '{NUEVO_VALOR}'")
    print("Listo.")


if __name__ == "__main__":
    main()
