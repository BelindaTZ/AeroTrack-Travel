"""Seed idempotente: KPI manual de CAC digital (OE-1, Balanced Scorecard)
en `configuracion_sistema` — docs/estrategico-auditoria.md sección 1.3
(bloqueante: no existe ninguna fuente real de costo de canal/campaña en
el sistema, así que este KPI se ingresa a mano por el admin en vez de
calcularse). Mismo patrón `valor` como string (igual que el resto de
`configuracion_sistema` — no hay tipado nativo por fila en PocketBase acá,
se castea en la app al leer) que usa `bootstrap_configuracion_sistema.py`.

Uso: python scripts/seed_kpi_cac_digital.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

PB_URL = os.getenv("PB_TRAVEL_URL", "http://localhost:8091")
PB_EMAIL = os.getenv("PB_TRAVEL_EMAIL", "")
PB_PASSWORD = os.getenv("PB_TRAVEL_PASSWORD", "")


def main() -> None:
    resp = requests.post(f"{PB_URL}/api/admins/auth-with-password",
                          json={"identity": PB_EMAIL, "password": PB_PASSWORD}, timeout=15)
    resp.raise_for_status()
    token = resp.json()["token"]
    H = {"Authorization": token}

    admin = requests.get(f"{PB_URL}/api/collections/usuarios/records",
                          headers=H, params={"filter": f'email="{PB_EMAIL}"'}, timeout=15).json()["items"]
    if not admin:
        print("XX No se encontró el usuario administrador en 'usuarios'.")
        sys.exit(1)
    modificado_por = admin[0]["id"]

    # "kpi_estrategico" no existe como opción del select `categoria` (schema
    # cerrado en PocketBase, ver estrategico-auditoria.md) — se reutiliza
    # "parametro_negocio", la misma categoría que ya usa la UI genérica de
    # WP-08 (`admin/configuracion.html`), coincide en propósito.
    filas = [
        ("cac_digital_actual", "0.0", "parametro_negocio",
         "OE-1 — Costo de Adquisición del Cliente digital (KPI manual, sin fuente real de costo de canal/campaña en el sistema — ver docs/estrategico-auditoria.md)"),
        # "" es rechazado por PocketBase (`valor` es required=true en el
        # esquema real, mismo quirk que memoria del proyecto ya documentó
        # para number/bool/json — acá aplica también a string vacío). Se
        # usa "—" como sentinel de "todavía sin definir".
        ("cac_digital_periodo", "—", "parametro_negocio",
         "Período al que corresponde el valor de cac_digital_actual (ej. 'Julio 2026'), ingresado junto con el valor"),
    ]

    for clave, valor, categoria, descripcion in filas:
        existente = requests.get(f"{PB_URL}/api/collections/configuracion_sistema/records",
                                  headers=H, params={"filter": f'clave="{clave}"'}, timeout=15).json()
        if existente.get("items"):
            print(f"= ya existe (no se sobreescribe): {clave}")
            continue
        resp = requests.post(f"{PB_URL}/api/collections/configuracion_sistema/records", headers=H, json={
            "clave": clave, "valor": valor, "categoria": categoria,
            "descripcion": descripcion, "modificado_por": modificado_por,
        }, timeout=15)
        if resp.status_code != 200:
            print(f"XX ERROR creando {clave}: {resp.status_code} {resp.text}")
            sys.exit(1)
        print(f"+ creada: {clave}")

    print("\nListo.")


if __name__ == "__main__":
    main()
