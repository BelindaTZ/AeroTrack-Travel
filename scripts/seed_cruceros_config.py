"""Siembra idempotente de la configuración de RF-CRU-005/006 (CU-O122/O123,
catálogo + disponibilidad sintética de Cruceros) — categorías `cruceros`
(credenciales Cruise Pricing API) y `disponibilidad_cruceros` (regla de
negocio de CU-O123) en `configuracion_sistema`.

Host confirmado funcionando en docs/apis-reference.md sección 13:
`cruise-pricing-api1.p.rapidapi.com`. CORREGIDO 2026-07-20: plan Basic
RapidAPI real es 100 req/mes (límite duro) + 10 req/min — el supuesto
previo de ~500k/mes venía de headers de rate-limit mal interpretados. Sin
rotación por ciudad (el endpoint `/cruises?limit=` no es por destino), pero
sí gateado por `app/shared/cuota_service.py` igual que Hoteles/Autos/
Actividades.

Re-ejecutable: si una clave ya existe con otro valor, se actualiza (no solo
se crea la primera vez) — así una corrida posterior con `CLAVES` ampliado
aplica el nuevo valor.

Ejecutar: python scripts/seed_cruceros_config.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")

CLAVES = [
    {
        "clave": "cruceros.rapidapi_key",
        "valor": RAPIDAPI_KEY,
        "categoria": "cruceros",
        "descripcion": "RF-CRU-005 — key de RapidAPI para Cruise Pricing API (cruise-pricing-api1.p.rapidapi.com)",
    },
    {
        "clave": "cruceros.rapidapi_host",
        "valor": "cruise-pricing-api1.p.rapidapi.com",
        "categoria": "cruceros",
        "descripcion": "RF-CRU-005 — host confirmado funcionando (docs/apis-reference.md sección 13)",
    },
    {
        "clave": "cruceros.limite_cruceros",
        "valor": "10",
        "categoria": "cruceros",
        "descripcion": "RF-CRU-005 — cantidad de cruceros a resolver en detalle por corrida (cada uno cuesta 1 llamada extra de detalle, más 2 fijas de navieras/búsqueda); con el límite duro real de 100 req/mes, mantenerlo bajo dejar margen para varias corridas al mes",
    },
    {
        "clave": "disponibilidad_cruceros.cupos_default",
        "valor": "20",
        "categoria": "disponibilidad_cruceros",
        "descripcion": "RF-CRU-006/CU-O123 — cupo aproximado por camarote (regla de negocio, sin fuente real de inventario confirmada)",
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
    if not RAPIDAPI_KEY:
        raise RuntimeError("RAPIDAPI_KEY no está en el .env local — no se puede sembrar el valor inicial")

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
        items_existentes = existente.json()["items"]
        valor_mostrado = "***" if "key" in entrada["clave"] else entrada["valor"]

        if items_existentes:
            actual = items_existentes[0]
            if actual["valor"] == entrada["valor"]:
                print(f"= {entrada['clave']} ya existe")
                continue
            actualizar = httpx.patch(
                f"{PB_URL}/api/collections/configuracion_sistema/records/{actual['id']}",
                json={"valor": entrada["valor"], "modificado_por": admin_id},
                headers=headers,
                timeout=10,
            )
            actualizar.raise_for_status()
            print(f"~ {entrada['clave']} actualizado a {valor_mostrado}")
            continue

        crear = httpx.post(
            f"{PB_URL}/api/collections/configuracion_sistema/records",
            json={**entrada, "modificado_por": admin_id},
            headers=headers,
            timeout=10,
        )
        crear.raise_for_status()
        print(f"+ {entrada['clave']} = {valor_mostrado}")


if __name__ == "__main__":
    main()
