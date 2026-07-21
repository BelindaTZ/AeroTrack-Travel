"""Completa el esquema heredado de `notificaciones` (colección creada en una
sesión anterior, antes de este módulo) para poder representar RF-DIS-006:

- `estado_envio` no incluía `fallido_definitivo` — sin él no hay forma de
  distinguir "puede reintentarse" de "reintentos agotados, constancia
  definitiva" (RN-DIS-006: nunca reintento silencioso indefinido).
- No existía ningún campo para contar reintentos ya realizados — se agrega
  `intentos_envio` (number, no requerido, representa 0 igual que
  `tarifas_vuelo.cupos_disponibles`).

Este módulo es dueño de `notificaciones` (a diferencia de Facturación, que
no lo era de sus colecciones y por eso se adaptó al esquema existente en vez
de modificarlo) — corregir el esquema aquí es la opción correcta, no un
ajuste de alcance.

Idempotente: no falla si ya se corrigió.

Ejecutar: python scripts/pb_schema_disrupciones_fix.py
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
    resp = httpx.get(f"{PB_URL}/api/collections/notificaciones", headers=headers, timeout=10)
    resp.raise_for_status()
    coleccion = resp.json()
    schema = coleccion.get("schema", coleccion.get("fields"))

    cambiado = False

    estado_envio = next(f for f in schema if f["name"] == "estado_envio")
    valores = estado_envio["options"]["values"]
    if "fallido_definitivo" not in valores:
        valores.append("fallido_definitivo")
        cambiado = True
        print("+ notificaciones.estado_envio ahora acepta 'fallido_definitivo'")
    else:
        print("= notificaciones.estado_envio ya acepta 'fallido_definitivo'")

    if not any(f["name"] == "intentos_envio" for f in schema):
        schema.append(
            {
                "name": "intentos_envio",
                "type": "number",
                "required": False,
                "presentable": False,
                "unique": False,
                "options": {"min": 0, "max": None, "noDecimal": True},
            }
        )
        cambiado = True
        print("+ notificaciones.intentos_envio creado (number, required=false)")
    else:
        print("= notificaciones.intentos_envio ya existe")

    if not cambiado:
        print("= nada que hacer")
        return

    patch = httpx.patch(
        f"{PB_URL}/api/collections/{coleccion['id']}",
        json={"schema": schema},
        headers=headers,
        timeout=10,
    )
    patch.raise_for_status()
    print("OK — esquema de notificaciones actualizado")


if __name__ == "__main__":
    main()
