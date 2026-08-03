"""Siembra idempotente de la configuración de RF-HOT-004/005 (CU-O118,
catálogo de Hoteles) — categoría `hoteles` en `configuracion_sistema`.
Mismo patrón que `api_estado_vuelo.*`/`tasas_cambio.*`: la key vive en
PocketBase, no se lee de variables de entorno en runtime.

Host confirmado funcionando en docs/apis-reference.md sección 5:
`hotellens.p.rapidapi.com`. Rate limit estricto (~4-5 llamadas/min, plan
BASIC) — `ciudades_seed` es una lista curada (no exhaustiva), pero cada
corrida solo toca `ciudades_por_corrida` de ellas, rotando por
día-del-año (ver `catalogo_service.generar_catalogo`) para no exceder el
rate limit por minuto en una sola corrida ampliada.

Re-ejecutable: si una clave ya existe con otro valor, se actualiza (no solo
se crea la primera vez) — así una corrida posterior con `CLAVES` ampliado
aplica el nuevo valor.

Ejecutar: python scripts/seed_hoteles_config.py
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
        "clave": "hoteles.rapidapi_key",
        "valor": RAPIDAPI_KEY,
        "categoria": "hoteles",
        "descripcion": "RF-HOT-004 — key de RapidAPI para HotelLens (hotellens.p.rapidapi.com)",
    },
    {
        "clave": "hoteles.rapidapi_host",
        "valor": "hotellens.p.rapidapi.com",
        "categoria": "hoteles",
        "descripcion": "RF-HOT-004 — host confirmado funcionando (docs/apis-reference.md sección 5)",
    },
    {
        "clave": "hoteles.ciudades_seed",
        "valor": (
            "Paris,Madrid,New York,Barcelona,Rome,London,Miami,Buenos Aires,Cancun,Tokyo,Dubai,"
            "Amsterdam,Berlin,Lisbon,Istanbul,Bangkok,Singapore,Sydney,Los Angeles,Chicago,Toronto,"
            "Mexico City,Rio de Janeiro,Lima,Bogota,Santiago,Seoul,Hong Kong,Vienna,Prague,Athens,"
            "Cairo,Marrakech,Cape Town,Bali,Phuket,Punta Cana,San Juan,Orlando,Las Vegas"
        ),
        "categoria": "hoteles",
        "descripcion": "RF-HOT-004 — universo curado de 40 ciudades, separadas por coma; cada corrida solo procesa una rebanada rotativa de tamaño hoteles.ciudades_por_corrida, y app/shared/cuota_service.py corta antes de exceder el límite duro real de HotelLens (100 req/mes, plan Basic RapidAPI)",
    },
    {
        "clave": "hoteles.ciudades_por_corrida",
        "valor": "3",
        "categoria": "hoteles",
        "descripcion": "RF-HOT-004 — cuántas ciudades de hoteles.ciudades_seed se procesan en una corrida (rotación por día-del-año); el gate de cuota mensual (app/shared/cuota_service.py) es la protección real, esto solo da variedad",
    },
    {
        "clave": "hoteles.max_hoteles_por_ciudad",
        "valor": "2",
        "categoria": "hoteles",
        "descripcion": "RF-HOT-004 — tope de hoteles a resolver en detalle (hasta 3 llamadas reales c/u: prices+booking_details+reviews) por corrida y por ciudad; con el límite duro de 100 req/mes, mantenerlo bajo estira el presupuesto a más ciudades distintas",
    },
    {
        "clave": "disponibilidad_hoteles.dias_adelante",
        "valor": "60",
        "categoria": "disponibilidad_hoteles",
        "descripcion": "Cuántas noches hacia adelante se genera disponibilidad sintética por tipo de habitación (hoteles_disponibilidad) — antes check-in/check-out eran cosméticos, ver errores-conocidos.md",
    },
    {
        "clave": "disponibilidad_hoteles.cupos_default",
        "valor": "10",
        "categoria": "disponibilidad_hoteles",
        "descripcion": "Cupo por noche cuando HotelLens no da un rooms_left real para esa tarifa (fallback, no inventario real de proveedor)",
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

    rol_admin = httpx.get(
        f"{PB_URL}/api/collections/roles/records",
        params={"filter": 'nombre="Administrador"', "perPage": 1},
        headers=headers,
        timeout=10,
    )
    rol_admin.raise_for_status()
    roles_items = rol_admin.json()["items"]
    if not roles_items:
        raise RuntimeError("No existe el rol 'Administrador' — correr scripts/seed_seguridad.py primero")
    resp = httpx.get(
        f"{PB_URL}/api/collections/usuarios/records",
        params={"filter": f'rol_id="{roles_items[0]["id"]}"', "perPage": 1},
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
