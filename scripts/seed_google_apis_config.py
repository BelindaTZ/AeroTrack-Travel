"""Siembra idempotente de la configuración de las 5 APIs de Google Cloud
que sí se van a usar (Places, Geocoding, Maps Embed, Maps JavaScript,
Routes) — categoría `google_apis` en `configuracion_sistema`. Mismo
patrón que `hoteles.*`/`api_estado_vuelo.*`: las keys viven en PocketBase,
no se leen de variables de entorno en runtime (REG-B3).

Deliberadamente NO se siembra nada para Gmail (key), Travel Impact Model
ni Travel Partner Prices — excluidas a pedido explícito del usuario
(2026-07-20): Gmail (key) es redundante con el Gmail OAuth que ya
funciona; las otras dos necesitan verificar partnership con Google antes
de asumir que son usables con una simple API key.

Límites diarios reales confirmados en Cuotas y Límites → IAM (2026-07-20):
Places (autocomplete/getPlace) 100/día, Routes (ComputeRoutes) 100/día.
Geocoding usa el endpoint CLÁSICO (`geocoding_client.py`), sin límite
diario configurado — por eso no lleva `limite_diario` aquí. Maps Embed y
Maps JavaScript no tienen cliente backend en este alcance (Embed es un
iframe que carga el navegador del usuario, no nuestro backend; JavaScript
API no tiene UI conectada todavía) — sus keys se siembran igual para que
ya estén listas.

Re-ejecutable: si una clave ya existe con otro valor, se actualiza.

Ejecutar: python scripts/seed_google_apis_config.py
"""

import datetime
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

HOY = datetime.date.today().isoformat()

CLAVES = [
    {
        "clave": "google_apis.places_api_key",
        "valor": os.environ.get("GOOGLE_CLOUD_PLACES_API_KEY", ""),
        "categoria": "google_apis",
        "descripcion": "Places API (New) — sin UI conectada todavía, base lista para el selector estilo Despegar",
    },
    {
        "clave": "google_apis.places_limite_diario",
        "valor": "100",
        "categoria": "google_apis",
        "descripcion": "Places API (New) — autocomplete/getPlace: 100/día real (Cuotas y Límites → IAM, 2026-07-20)",
    },
    {
        "clave": "google_apis.places_usadas_dia",
        "valor": "0",
        "categoria": "google_apis",
        "descripcion": "Contador diario, lo actualiza app/shared/cuota_service.registrar_uso_diario",
    },
    {
        "clave": "google_apis.places_periodo_actual",
        "valor": HOY,
        "categoria": "google_apis",
        "descripcion": "Fecha (YYYY-MM-DD) del período actual del contador diario de Places",
    },
    {
        "clave": "google_apis.geocoding_api_key",
        "valor": os.environ.get("GOOGLE_CLOUD_GEOCODING_API_KEY", ""),
        "categoria": "google_apis",
        "descripcion": "Geocoding API — geocoding_client.py usa el endpoint clásico, sin límite diario configurado",
    },
    {
        "clave": "google_apis.maps_embed_api_key",
        "valor": os.environ.get("GOOGLE_CLOUD_MAPS_EMBED_API_KEY", ""),
        "categoria": "google_apis",
        "descripcion": "Maps Embed API — conectada en detalle de hotel (ubicación) y crucero (ruta), sin cuota configurada",
    },
    {
        "clave": "google_apis.maps_javascript_api_key",
        "valor": os.environ.get("GOOGLE_CLOUD_MAPS_JAVASCRIPT_API_KEY", ""),
        "categoria": "google_apis",
        "descripcion": "Maps JavaScript API — sin UI conectada todavía (necesita el primer JS propio del proyecto)",
    },
    {
        "clave": "google_apis.routes_api_key",
        "valor": os.environ.get("GOOGLE_CLOUD_ROUTES_API_KEY", ""),
        "categoria": "google_apis",
        "descripcion": "Routes API — sin UI conectada todavía, candidata a 'distancia al centro' en tarjetas de hotel",
    },
    {
        "clave": "google_apis.routes_limite_diario",
        "valor": "100",
        "categoria": "google_apis",
        "descripcion": "Routes API (ComputeRoutes): 100/día real (Cuotas y Límites → IAM, 2026-07-20)",
    },
    {
        "clave": "google_apis.routes_usadas_dia",
        "valor": "0",
        "categoria": "google_apis",
        "descripcion": "Contador diario, lo actualiza app/shared/cuota_service.registrar_uso_diario",
    },
    {
        "clave": "google_apis.routes_periodo_actual",
        "valor": HOY,
        "categoria": "google_apis",
        "descripcion": "Fecha (YYYY-MM-DD) del período actual del contador diario de Routes",
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
