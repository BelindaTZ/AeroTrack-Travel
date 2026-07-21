"""Siembra idempotente del default global de acumulación cupón+paquete
(CU-T44, resuelve QP-18) — `configuracion_sistema` no tenía esta clave
todavía. Default elegido: "false" (no acumulable salvo excepción explícita
por cupón vía `cupones_descuento.acumulable_con_paquete`) — protege margen
por defecto; un Administrador lo cambia desde CU-T30 una vez exista
`router_config_acumulacion.py` (specs/tactico/ofertas-promociones/tasks.md
T012, pendiente de código).

Ejecutar: python scripts/seed_ofertas_config.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

CLAVES = [
    {
        "clave": "cupones.acumulable_con_paquete_default",
        "valor": "false",
        "categoria": "cupones",
        "descripcion": "CU-T44 — default global: si un cupón sin excepción explícita es acumulable con el descuento propio de un paquete (RN-OFE-T03)",
    },
]


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

    resp = httpx.get(
        f"{PB_URL}/api/collections/usuarios/records",
        params={"filter": 'tipo_actor="administrador"', "perPage": 1},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json()["items"]
    if not items:
        raise RuntimeError("No hay ningún usuario administrador sembrado")
    admin_id = items[0]["id"]

    for entrada in CLAVES:
        existente = httpx.get(
            f"{PB_URL}/api/collections/configuracion_sistema/records",
            params={"filter": f'clave="{entrada["clave"]}"', "perPage": 1},
            headers=headers,
            timeout=10,
        )
        existente.raise_for_status()
        if existente.json()["items"]:
            print(f"= {entrada['clave']} ya existe")
            continue

        crear = httpx.post(
            f"{PB_URL}/api/collections/configuracion_sistema/records",
            json={**entrada, "modificado_por": admin_id},
            headers=headers,
            timeout=10,
        )
        crear.raise_for_status()
        print(f"+ {entrada['clave']} = {entrada['valor']}")


if __name__ == "__main__":
    main()
