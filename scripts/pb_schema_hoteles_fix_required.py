"""Corrige el mismo defecto ya documentado para `tarifas_vuelo.cupos_disponibles`
(errores-conocidos.md): PocketBase 0.22 valida "required" en campos
numéricos/booleanos tratando 0/false como valor ausente ("Missing required
value"), lo cual rompe casos legítimos donde la API real de HotelLens
devuelve `total_price: null` (rooms de pago en destino, sin prepago) o
`free_cancellation: false` (habitación no reembolsable, el caso más común).

Confirmado en vivo 2026-07-19 al correr `catalogo_service.generar_catalogo`
contra la API real: `hoteles_tarifas.precio_final=0.0` y
`.reembolsable=False` rechazados con `validation_required` pese a ser
valores válidos, no ausentes.

Idempotente.

Ejecutar: python scripts/pb_schema_hoteles_fix_required.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

CAMPOS = ["precio_final", "reembolsable"]


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
    resp = httpx.get(f"{PB_URL}/api/collections/hoteles_tarifas", headers=headers, timeout=10)
    resp.raise_for_status()
    coleccion = resp.json()
    schema = coleccion.get("schema", coleccion.get("fields"))

    cambiado = False
    for nombre_campo in CAMPOS:
        campo = next(f for f in schema if f["name"] == nombre_campo)
        if not campo["required"]:
            print(f"= hoteles_tarifas.{nombre_campo} ya es required=false")
            continue
        campo["required"] = False
        cambiado = True
        print(f"+ hoteles_tarifas.{nombre_campo} ahora es required=false")

    if not cambiado:
        print("= nada que hacer")
        return

    patch = httpx.patch(
        f"{PB_URL}/api/collections/{coleccion['id']}", json={"schema": schema}, headers=headers, timeout=10
    )
    if patch.status_code >= 400:
        print(f"! posible 400 cosmético (ver nota en pb_schema_vuelos_v3.py): {patch.text}")
    print("Listo.")


if __name__ == "__main__":
    main()
