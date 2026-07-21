"""Marca `reservas.vuelo_id`/`tarifa_id` como `required=false`.

Precondición real de Reservas 1.4 (adoptar `reserva_items`): el producto
reservado deja de vivir exclusivamente en la cabecera — una reserva-paquete
(CU-O76, ≥2 `tipo_producto` en `reserva_items`) no tiene un único
vuelo_id/tarifa_id que la represente. El flujo actual (solo Vuelos) sigue
escribiendo ambos campos siempre (dual-write con `reserva_items`, ver
`crear_reserva_service.py`) — este cambio de esquema solo LOOSENS la
restricción para permitir que un futuro creador de paquetes deje esos
campos vacíos; no afecta ninguna fila/flujo existente (0 `reservas` reales
en este momento, ver `scripts/limpiar_datos_demo_reservas.py`).

Idempotente.

Ejecutar: python scripts/pb_schema_reservas_fix_opcionales.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

CAMPOS = ["vuelo_id", "tarifa_id"]


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
    resp = httpx.get(f"{PB_URL}/api/collections/reservas", headers=headers, timeout=10)
    resp.raise_for_status()
    coleccion = resp.json()
    schema = coleccion.get("schema", coleccion.get("fields"))

    cambiado = False
    for nombre_campo in CAMPOS:
        campo = next(f for f in schema if f["name"] == nombre_campo)
        if not campo["required"]:
            print(f"= reservas.{nombre_campo} ya es required=false")
            continue
        campo["required"] = False
        cambiado = True
        print(f"+ reservas.{nombre_campo} ahora es required=false")

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
