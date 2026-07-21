"""Siembra idempotente de la configuración de RF-FAC-011 (CU-O85, conversión
de moneda) — categoría `tasas_cambio` en `configuracion_sistema`. Mismo
patrón que `api_estado_vuelo.*` (AviationStack): la API key vive en
`configuracion_sistema`, no en variables de entorno leídas en runtime
(permite rotarla desde el backoffice sin redeploy, CU-O17).

`rapidapi_key` se toma UNA VEZ del `.env` local (`RAPIDAPI_KEY`) para
sembrar el valor inicial — después de este seed, la fuente de verdad en
ejecución es PocketBase, no el `.env` (mismo criterio que ya usa
AviationStack). Host confirmado funcionando en docs/apis-reference.md
sección 10: `exchange-rate-api1.p.rapidapi.com` (con guiones).

Ejecutar: python scripts/seed_tasas_cambio_config.py
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
        "clave": "tasas_cambio.rapidapi_key",
        "valor": RAPIDAPI_KEY,
        "categoria": "tasas_cambio",
        "descripcion": "RF-FAC-011 — key de RapidAPI para ExchangeRate-API (exchange-rate-api1.p.rapidapi.com)",
    },
    {
        "clave": "tasas_cambio.rapidapi_host",
        "valor": "exchange-rate-api1.p.rapidapi.com",
        "categoria": "tasas_cambio",
        "descripcion": "RF-FAC-011 — host confirmado funcionando (docs/apis-reference.md sección 10; el host sin guiones da 403)",
    },
    {
        "clave": "tasas_cambio.moneda_base",
        "valor": "USD",
        "categoria": "tasas_cambio",
        "descripcion": "RF-FAC-011 — moneda en la que se cobra siempre vía Stripe; base de la conversión de presentación",
    },
    {
        "clave": "tasas_cambio.monedas_destino",
        "valor": "EUR,GBP,MXN,CAD,COP,BRL",
        "categoria": "tasas_cambio",
        "descripcion": "RF-FAC-011 — monedas locales relevantes para presentación (mercados donde opera la agencia), separadas por coma",
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
        valor_mostrado = "***" if "key" in entrada["clave"] else entrada["valor"]
        print(f"+ {entrada['clave']} = {valor_mostrado}")


if __name__ == "__main__":
    main()
