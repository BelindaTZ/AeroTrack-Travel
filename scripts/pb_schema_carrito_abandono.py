"""Migración de esquema — Abandono de carrito (CU-T26/T27, RF-CAR-T01/T02).

`carritos.estado` ya soporta el valor `abandonado` desde
`pb_schema_carrito.py`, pero no hay forma de saber, una vez que un carrito
vuelve a `activo` y luego a `convertido`, que pasó por abandono alguna vez
(el `estado` final ya no lo dice). Se agrega:

- `carritos.fue_abandonado` (bool) — única fuente de verdad para CU-T27:
  se marca `true` la primera vez que el job de detección lo abandona y
  nunca se resetea, aunque el carrito se reactive después.
- `carritos.fecha_marcado_abandonado` (date) — para filtrar el reporte por
  período (REG-J9).

También siembra `configuracion_sistema` (categoría `carrito_abandonado`):
umbral de inactividad y plantilla del email de recordatorio (RF-CAR-T01).

Idempotente en ambas partes.

Ejecutar: python scripts/pb_schema_carrito_abandono.py
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

DEFAULT_UMBRAL_HORAS = "2"
DEFAULT_ASUNTO = "¿Olvidaste algo en tu carrito?"
DEFAULT_CUERPO = (
    "Todavía tienes productos esperando en tu carrito de AeroTrack Travel. "
    "Vuelve para completar tu reserva antes de que se agote el cupo."
)


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


def ensure_fields(headers: dict, collection: dict, nuevos_campos: list[dict]) -> None:
    existentes = {f["name"] for f in collection["schema"]}
    faltantes = [f for f in nuevos_campos if f["name"] not in existentes]
    if not faltantes:
        print(f"  = {collection['name']}: campos ya presentes, se omite")
        return
    schema_actualizado = collection["schema"] + faltantes
    resp = httpx.patch(
        f"{PB_URL}/api/collections/{collection['id']}",
        json={"schema": schema_actualizado},
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        print(f"  ! error agregando campos a {collection['name']}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    print(f"  + {collection['name']}: agregados {[f['name'] for f in faltantes]}")


def bool_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "bool", "required": required, "options": {}}


def date_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "date", "required": required, "options": {}}


def main() -> None:
    headers = {"Authorization": admin_token()}

    print("Actualizando carritos...")
    carritos = get_collection(headers, "carritos")
    ensure_fields(
        headers, carritos,
        [bool_field("fue_abandonado"), date_field("fecha_marcado_abandonado")],
    )

    print("Sembrando configuracion_sistema.carrito_abandonado...")
    admin_resp = httpx.get(
        f"{PB_URL}/api/collections/usuarios/records",
        headers=headers, params={"filter": f'email="{PB_EMAIL}"'}, timeout=10,
    )
    admin_resp.raise_for_status()
    admins = admin_resp.json()["items"]
    if not admins:
        print("  ! no se encontró el usuario administrador en 'usuarios' — se omite el seed de config", file=sys.stderr)
        return
    modificado_por = admins[0]["id"]

    filas = [
        ("carrito_abandonado.umbral_horas_inactividad", DEFAULT_UMBRAL_HORAS,
         "Horas de inactividad tras las cuales un carrito activo se marca abandonado (RF-CAR-T01)"),
        ("carrito_abandonado.plantilla_asunto", DEFAULT_ASUNTO,
         "Asunto del email de recordatorio de carrito abandonado (RF-CAR-T01)"),
        ("carrito_abandonado.plantilla_cuerpo", DEFAULT_CUERPO,
         "Cuerpo del email de recordatorio de carrito abandonado (RF-CAR-T01)"),
    ]
    for clave, valor, descripcion in filas:
        existente = httpx.get(
            f"{PB_URL}/api/collections/configuracion_sistema/records",
            headers=headers, params={"filter": f'clave="{clave}"'}, timeout=10,
        )
        existente.raise_for_status()
        if existente.json()["items"]:
            print(f"  = {clave}: ya existe, se omite")
            continue
        creado = httpx.post(
            f"{PB_URL}/api/collections/configuracion_sistema/records",
            json={
                "clave": clave,
                "valor": valor,
                "categoria": "carrito_abandonado",
                "descripcion": descripcion,
                "modificado_por": modificado_por,
            },
            headers=headers, timeout=10,
        )
        if creado.status_code >= 400:
            print(f"  ! error creando {clave}: {creado.text}", file=sys.stderr)
            creado.raise_for_status()
        print(f"  + {clave} = {valor}")

    print("Listo.")


if __name__ == "__main__":
    main()
