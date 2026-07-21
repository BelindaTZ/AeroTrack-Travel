"""Agrega `usuarios.foto_perfil` (file field), campo nuevo del dbml v3 que
faltaba por completo del esquema anterior (RF-SEG-006, CU-O05) — ver nota en
docs/aerotrack-travel-propuesta-tablas-v3.dbml línea 466 y
specs/operativo/seguridad/checklist.md CHK050.

Idempotente: no falla si el campo ya existe.

Ejecutar: python scripts/pb_schema_seguridad_fix_foto_perfil.py
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
    resp = httpx.get(f"{PB_URL}/api/collections/usuarios", headers=headers, timeout=10)
    resp.raise_for_status()
    coleccion = resp.json()
    schema = coleccion.get("schema", coleccion.get("fields"))

    if any(f["name"] == "foto_perfil" for f in schema):
        print("= usuarios.foto_perfil ya existe, nada que hacer")
        return

    schema.append(
        {
            "name": "foto_perfil",
            "type": "file",
            "required": False,
            "options": {
                "maxSelect": 1,
                "maxSize": 5242880,  # 5 MB
                "mimeTypes": ["image/jpeg", "image/png", "image/webp"],
            },
        }
    )
    patch = httpx.patch(
        f"{PB_URL}/api/collections/{coleccion['id']}",
        json={"schema": schema},
        headers=headers,
        timeout=10,
    )
    patch.raise_for_status()
    print("+ usuarios.foto_perfil creado (file, required=false, jpeg/png/webp, máx 5MB)")


if __name__ == "__main__":
    main()
