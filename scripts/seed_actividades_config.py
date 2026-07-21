"""Siembra idempotente de la configuración de RF-ACT-004/005/006
(CU-O120/O121, catálogo + disponibilidad sintética de Actividades) —
categorías `actividades` (credenciales Travel Advisor) y
`disponibilidad_actividades` (regla de negocio de CU-O121/CU-T42) en
`configuracion_sistema`.

Host confirmado funcionando en docs/apis-reference.md sección 18:
`travel-advisor.p.rapidapi.com`. Corrección: el panel real de RapidAPI
confirma plan Basic con límite DURO de 500 req/mes (+ 5 req/seg) — no
"sin cuota documentada" como se asumió antes. `ciudades_seed` es un
universo curado de 40 ciudades y cada corrida solo toca
`ciudades_por_corrida` de ellas, rotando por día-del-año (ver
`catalogo_service.generar_catalogo`); el gate real que impide pasarse del
techo es `app/shared/cuota_service.py`. Los valores de
`disponibilidad_actividades` se siembran aquí directamente
(Integraciones/CU-T42 no tienen UI de edición todavía) — mismo criterio que
usó Vuelos con Seguridad al principio.

Re-ejecutable: si una clave ya existe con otro valor, se actualiza (no solo
se crea la primera vez) — así una corrida posterior con `CLAVES` ampliado
aplica el nuevo valor.

Ejecutar: python scripts/seed_actividades_config.py
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
        "clave": "actividades.rapidapi_key",
        "valor": RAPIDAPI_KEY,
        "categoria": "actividades",
        "descripcion": "RF-ACT-004 — key de RapidAPI para Travel Advisor (travel-advisor.p.rapidapi.com)",
    },
    {
        "clave": "actividades.rapidapi_host",
        "valor": "travel-advisor.p.rapidapi.com",
        "categoria": "actividades",
        "descripcion": "RF-ACT-004 — host confirmado funcionando (docs/apis-reference.md sección 18)",
    },
    {
        "clave": "actividades.ciudades_seed",
        "valor": (
            "Paris,Madrid,New York,Barcelona,Rome,London,Miami,Buenos Aires,Cancun,Tokyo,Dubai,"
            "Amsterdam,Berlin,Lisbon,Istanbul,Bangkok,Singapore,Sydney,Los Angeles,Chicago,Toronto,"
            "Mexico City,Rio de Janeiro,Lima,Bogota,Santiago,Seoul,Hong Kong,Vienna,Prague,Athens,"
            "Cairo,Marrakech,Cape Town,Bali,Phuket,Punta Cana,San Juan,Orlando,Las Vegas"
        ),
        "categoria": "actividades",
        "descripcion": "RF-ACT-004 — universo curado de 40 ciudades, separadas por coma; cada corrida solo procesa una rebanada rotativa de tamaño actividades.ciudades_por_corrida, y app/shared/cuota_service.py corta antes de exceder el límite duro real de Travel Advisor (500 req/mes, plan Basic RapidAPI)",
    },
    {
        "clave": "actividades.ciudades_por_corrida",
        "valor": "4",
        "categoria": "actividades",
        "descripcion": "RF-ACT-004 — cuántas ciudades de actividades.ciudades_seed se procesan en una corrida (rotación por día-del-año, cubre el universo completo en varias corridas)",
    },
    {
        "clave": "actividades.max_actividades_por_ciudad",
        "valor": "3",
        "categoria": "actividades",
        "descripcion": "RF-ACT-004 — tope de actividades a resolver en detalle por corrida y por ciudad (cada una cuesta 1 llamada extra de detalle)",
    },
    {
        "clave": "disponibilidad_actividades.cupos_default",
        "valor": "15",
        "categoria": "disponibilidad_actividades",
        "descripcion": "RF-ACT-006/CU-O121 — cupo aproximado por horario (regla de negocio, sin fuente real de inventario confirmada)",
    },
    {
        "clave": "disponibilidad_actividades.horarios_por_dia",
        "valor": "09:00,13:00,16:00",
        "categoria": "disponibilidad_actividades",
        "descripcion": "RF-ACT-006/CU-O121 — horarios generados por día, separados por coma",
    },
    {
        "clave": "disponibilidad_actividades.dias_adelante",
        "valor": "14",
        "categoria": "disponibilidad_actividades",
        "descripcion": "RF-ACT-006/CU-O121 — ventana móvil de días hacia adelante para los que se genera disponibilidad",
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
