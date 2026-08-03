"""Siembra idempotente de la configuración de RF-VUE-001/CU-O30 —
enriquecimiento real del catálogo de vuelos (AeroDataBox + Google Flights
vía SerpApi) — categoría `api_estado_vuelo`... no, categoría propia
`vuelos` en `configuracion_sistema`. Mismo patrón que `hoteles.*`.

Host/credenciales confirmados funcionando en docs/apis-reference.md
sección 2 (AeroDataBox) y docs/google-flights-serpapi-hallazgos.md
(SerpApi). Límites duros reales confirmados por el usuario en el panel de
cada proveedor (2026-07-21): AeroDataBox 600 unidades/mes + 2.400
requests/mes; Google Flights (SerpApi) 250 búsquedas/mes.

Re-ejecutable: si una clave ya existe con otro valor, se actualiza.

Ejecutar: python scripts/seed_vuelos_config.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
AERODATABOX_API_HOST = os.environ.get("AERODATABOX_API_HOST", "")
GOOGLE_FLIGHTS_API_KEY = os.environ.get("GOOGLE_FLIGHTS_API_KEY", "")

# Mismos 15 hubs curados que dags/catalogo_vuelos_tasks.py (HUBS) — deben
# coincidir, si no la rotación de enriquecimiento apunta a hubs que el
# catálogo sintético nunca genera.
HUBS_CURADOS = "ATL,ORD,DFW,DEN,LAX,JFK,SFO,LAS,MCO,PHX,MIA,SEA,EWR,CLT,IAH"

CLAVES = [
    {
        "clave": "vuelos.aerodatabox_api_key",
        "valor": RAPIDAPI_KEY,
        "categoria": "vuelos",
        "descripcion": "RF-VUE-001 — key de RapidAPI para AeroDataBox (misma cuenta que Hoteles/Autos/Actividades/Cruceros)",
    },
    {
        "clave": "vuelos.aerodatabox_api_host",
        "valor": AERODATABOX_API_HOST,
        "categoria": "vuelos",
        "descripcion": "RF-VUE-001 — host confirmado funcionando (docs/apis-reference.md sección 2)",
    },
    {
        "clave": "vuelos.aerodatabox_hubs",
        "valor": HUBS_CURADOS,
        "categoria": "vuelos",
        "descripcion": "RF-VUE-001 — universo curado de 15 hubs (debe coincidir con dags/catalogo_vuelos_tasks.py HUBS); cada corrida solo procesa una rebanada rotativa de tamaño vuelos.aerodatabox_hubs_por_corrida",
    },
    {
        "clave": "vuelos.aerodatabox_hubs_por_corrida",
        "valor": "3",
        "categoria": "vuelos",
        "descripcion": "RF-VUE-001 — cuántos hubs se procesan por corrida (rotación por día-del-año); con el límite duro real de 600 unidades/mes (~2 u/llamada FIDS, 2 llamadas/hub), 3 hubs/día ≈ 360/mes",
    },
    {
        "clave": "vuelos.google_flights_api_key",
        "valor": GOOGLE_FLIGHTS_API_KEY,
        "categoria": "vuelos",
        "descripcion": "RF-VUE-001 — key de SerpApi (cuenta aparte, no RapidAPI) para Google Flights (engine=google_flights)",
    },
    {
        "clave": "vuelos.google_flights_rutas_por_corrida",
        "valor": "3",
        "categoria": "vuelos",
        "descripcion": "RF-VUE-001 — cuántas rutas curadas se procesan por corrida (rotación por día-del-año); con el límite duro real de 250 búsquedas/mes, 3 rutas/día ≈ 90/mes, deja margen para refrescar clases de cabina",
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
    faltantes = [c["clave"] for c in CLAVES if "api_key" in c["clave"] and not c["valor"]]
    if faltantes:
        raise RuntimeError(f"Faltan estas keys en .env: {faltantes}")

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
