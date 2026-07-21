"""Agrega las 9 categorías nuevas de `configuracion_sistema.categoria` que
documenta el dbml v3 (línea ~528) y que todavía faltaban en el select real
de PocketBase: asistente_ia, carrito_abandonado, programa_beneficios,
politica_contrasenas, disponibilidad_actividades, disponibilidad_cruceros,
disponibilidad_tarifas_vuelo, disponibilidad_asientos, cupones.

Bloqueaba sembrar `cupones.acumulable_con_paquete_default` (CU-T44) — el
select vivo solo tenía las 11 categorías originales (pre-v3).

Idempotente.

Ejecutar: python scripts/pb_schema_configuracion_categorias_v3.py
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

CATEGORIAS_NUEVAS = [
    "asistente_ia",
    "carrito_abandonado",
    "programa_beneficios",
    "politica_contrasenas",
    "disponibilidad_actividades",
    "disponibilidad_cruceros",
    "disponibilidad_tarifas_vuelo",
    "disponibilidad_asientos",
    "cupones",
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
    resp = httpx.get(f"{PB_URL}/api/collections/configuracion_sistema", headers=headers, timeout=10)
    resp.raise_for_status()
    c = resp.json()
    schema = c.get("schema", c.get("fields"))
    f = next(x for x in schema if x["name"] == "categoria")
    actuales = f["options"]["values"]

    faltantes = [v for v in CATEGORIAS_NUEVAS if v not in actuales]
    if not faltantes:
        print("= todas las categorías ya existen, nada que hacer")
        return

    vistos: list[str] = []
    for v in actuales + faltantes:
        if v not in vistos:
            vistos.append(v)
    f["options"]["values"] = vistos

    patch = httpx.patch(
        f"{PB_URL}/api/collections/{c['id']}",
        json={"schema": schema},
        headers=headers,
        timeout=10,
    )
    if patch.status_code >= 400:
        print(f"! error (puede haberse aplicado igual, ver nota en pb_schema_vuelos_v3.py): {patch.text}", file=sys.stderr)
    print(f"+ categoria: agregadas {faltantes}")


if __name__ == "__main__":
    main()
