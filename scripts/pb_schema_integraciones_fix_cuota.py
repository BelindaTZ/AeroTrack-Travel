"""Agrega `cuota_mensual_estimada` (number, no requerido) a
`fuentes_datos_externas` — plan de consumo de cuota para los catálogos
periódicos de Hoteles/Autos/Actividades/Cruceros (mismo espíritu que
`api_estado_vuelo.limite_mensual` ya usa para AviationStack, pero
informacional: no todas las fuentes tienen un techo mensual confirmado,
ver `scripts/seed_fuentes_datos_externas.py`).

No se agrega un contador mensual mutable aparte (`unidades_consumidas_mes_actual`)
para evitar una segunda fuente de verdad — el consumo real ya queda
auditado en `sincronizaciones_log.unidades_cuota_consumidas` (campo que ya
existía en el esquema pero ningún `catalogo_service.py` lo llenaba; eso se
corrige en el código de cada servicio, no en el esquema).

Idempotente, mismo patrón que scripts/pb_schema_hoteles_fix_required.py.

Ejecutar: python scripts/pb_schema_integraciones_fix_cuota.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]


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
    resp = httpx.get(f"{PB_URL}/api/collections/fuentes_datos_externas", headers=headers, timeout=10)
    resp.raise_for_status()
    coleccion = resp.json()
    schema = coleccion.get("schema", coleccion.get("fields"))

    if any(f["name"] == "cuota_mensual_estimada" for f in schema):
        print("= fuentes_datos_externas.cuota_mensual_estimada ya existe")
        return

    schema.append({"name": "cuota_mensual_estimada", "type": "number", "required": False, "options": {}})

    patch = httpx.patch(
        f"{PB_URL}/api/collections/{coleccion['id']}", json={"schema": schema}, headers=headers, timeout=10
    )
    if patch.status_code >= 400:
        print(f"! posible 400 cosmético (ver nota en pb_schema_vuelos_v3.py): {patch.text}")
    print("+ fuentes_datos_externas.cuota_mensual_estimada agregado")
    print("Listo.")


if __name__ == "__main__":
    main()
