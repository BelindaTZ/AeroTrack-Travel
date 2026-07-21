"""Siembra idempotente (upsert por `combinacion`) de `tipos_paquete_descuento`
(RF-PAQ-002, CU-T14) — la colección estaba en esquema desde la migración
v3 pero nunca se sembró con datos reales. CU-T14 (Táctico, sin UI de
edición todavía) normalmente gobernaría estos valores desde el backoffice;
mientras tanto se siembran defaults directos, mismo criterio que
`disponibilidad_actividades`/`disponibilidad_cruceros`.

Ejecutar: python scripts/seed_tipos_paquete_descuento.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

# vuelo+hotel es la única combinación obligatoria (RN-PAQ-001) — el resto
# suma auto/actividad opcionales, con más descuento cuantos más componentes.
COMBINACIONES = [
    ("vuelo+hotel", 10.0),
    ("vuelo+hotel+auto", 12.0),
    ("vuelo+hotel+actividad", 12.0),
    ("vuelo+hotel+auto+actividad", 15.0),
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

    for combinacion, porcentaje in COMBINACIONES:
        existente = httpx.get(
            f"{PB_URL}/api/collections/tipos_paquete_descuento/records",
            params={"filter": f'combinacion="{combinacion}"', "perPage": 1},
            headers=headers,
            timeout=10,
        )
        existente.raise_for_status()
        if existente.json()["items"]:
            print(f"= {combinacion} ya existe")
            continue

        crear = httpx.post(
            f"{PB_URL}/api/collections/tipos_paquete_descuento/records",
            json={"combinacion": combinacion, "porcentaje_descuento": porcentaje, "activo": True},
            headers=headers,
            timeout=10,
        )
        crear.raise_for_status()
        print(f"+ {combinacion} = {porcentaje}%")


if __name__ == "__main__":
    main()
