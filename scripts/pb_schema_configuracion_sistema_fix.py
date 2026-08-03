"""Ampliación de WP-08 (sesión 2026-08-01): `configuracion_sistema.categoria`
es un select con valores fijos — agrega las 3 categorías nuevas usadas por
`scripts/seed_plantillas_flags_parametros.py` (plantillas de notificación,
feature flags, parámetros de negocio). Idempotente.

Ejecutar: python scripts/pb_schema_configuracion_sistema_fix.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

NUEVAS_CATEGORIAS = ["plantilla_notificacion", "feature_flag", "parametro_negocio"]


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

    categoria = next(f for f in schema if f["name"] == "categoria")
    valores = categoria["options"]["values"]

    agregadas = [v for v in NUEVAS_CATEGORIAS if v not in valores]
    if not agregadas:
        print("= configuracion_sistema.categoria ya acepta las 3 categorías nuevas")
        return

    valores.extend(agregadas)
    patch = httpx.patch(
        f"{PB_URL}/api/collections/{coleccion['id']}",
        json={"schema": schema},
        headers=headers,
        timeout=10,
    )
    patch.raise_for_status()
    print(f"+ configuracion_sistema.categoria ahora acepta: {', '.join(agregadas)}")


if __name__ == "__main__":
    main()
