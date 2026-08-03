"""Siembra idempotente de la configuración de RF-AUT-004 (CU-O119,
catálogo de Autos) — categoría `autos` en `configuracion_sistema`. Mismo
patrón que `hoteles.*`/`api_estado_vuelo.*`.

Host confirmado funcionando en docs/apis-reference.md sección 8:
`global-rental-cars.p.rapidapi.com`. Corrección importante: el panel real
de RapidAPI confirma plan Basic con límite DURO de 100 req/mes (+ 1000
req/hora) — la ausencia de 429/402 en las 26 pruebas anteriores no
significaba "sin cuota", solo que esas pruebas no se acercaron al techo
mensual. Por eso ahora `ciudades_seed` es un universo curado grande (40) y
cada corrida solo procesa una rebanada rotativa (`ciudades_por_corrida`),
igual que Hoteles/Actividades — el gate real que impide pasarse del techo
es `app/shared/cuota_service.py`, la rotación solo da variedad.

Re-ejecutable: si una clave ya existe con otro valor, se actualiza (no solo
se crea la primera vez) — así una corrida posterior con `CLAVES` ampliado
aplica el nuevo valor.

Ejecutar: python scripts/seed_autos_config.py
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
        "clave": "autos.rapidapi_key",
        "valor": RAPIDAPI_KEY,
        "categoria": "autos",
        "descripcion": "RF-AUT-004 — key de RapidAPI para Global Rental Cars (global-rental-cars.p.rapidapi.com)",
    },
    {
        "clave": "autos.rapidapi_host",
        "valor": "global-rental-cars.p.rapidapi.com",
        "categoria": "autos",
        "descripcion": "RF-AUT-004 — host confirmado funcionando (docs/apis-reference.md sección 8)",
    },
    {
        "clave": "autos.ciudades_seed",
        "valor": (
            "Paris,Madrid,New York,Barcelona,Rome,London,Miami,Buenos Aires,Cancun,Tokyo,Dubai,"
            "Amsterdam,Berlin,Lisbon,Istanbul,Bangkok,Singapore,Sydney,Los Angeles,Chicago,Toronto,"
            "Mexico City,Rio de Janeiro,Lima,Bogota,Santiago,Seoul,Hong Kong,Vienna,Prague,Athens,"
            "Cairo,Marrakech,Cape Town,Bali,Phuket,Punta Cana,San Juan,Orlando,Las Vegas"
        ),
        "categoria": "autos",
        "descripcion": "RF-AUT-004 — universo curado de 40 ciudades, separadas por coma; cada corrida solo procesa una rebanada rotativa de tamaño autos.ciudades_por_corrida, y app/shared/cuota_service.py corta antes de exceder el límite duro real de Global Rental Cars (100 req/mes, plan Basic RapidAPI)",
    },
    {
        "clave": "autos.ciudades_por_corrida",
        "valor": "2",
        "categoria": "autos",
        "descripcion": "RF-AUT-004 — cuántas ciudades de autos.ciudades_seed se procesan en una corrida (rotación por día-del-año); el gate de cuota mensual es la protección real, esto solo da variedad",
    },
    {
        "clave": "disponibilidad_autos.dias_adelante",
        "valor": "30",
        "categoria": "disponibilidad_autos",
        "descripcion": "Cuántos días hacia adelante se genera disponibilidad sintética por auto (autos_disponibilidad) — antes recogida/devolución eran cosméticas, ver errores-conocidos.md",
    },
    {
        "clave": "disponibilidad_autos.cupos_default",
        "valor": "5",
        "categoria": "disponibilidad_autos",
        "descripcion": "Cupo por día — Global Rental Cars no da señal de flota real, es regla de negocio interna (mismo criterio que actividades_horarios.cupos_disponibles)",
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
