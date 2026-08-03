"""Migración de esquema — Selección de asiento (CU-O114–O117, RF-VUE-010/011/012/013).

`asientos_vuelo` y `reserva_pasajeros.asiento_id`/`asiento_asignado_por` ya
existían en el esquema (`pb_schema_vuelos_v3.py`/`pb_schema_reservas_v3.py`,
sin código de aplicación todavía). Lo único que faltaba en el esquema real
para poder implementar la regla de negocio de RF-VUE-012 era:

- `niveles_tarifa.seleccion_asiento_temprana` (bool) — Standard/Flex=true,
  Light=false (RN confirmada en `specs/operativo/vuelos/vuelos-spec.md`).
- `configuracion_sistema.disponibilidad_asientos.*` — recargo/proporción de
  asientos premium y ventana de check-in gratuito (RN-VUE-T03: valores por
  defecto documentados en código hasta que el nivel Táctico CU-T39/40/41 se
  implemente; este script siembra esos defaults, no un valor inventado).

Idempotente en ambas partes.

Ejecutar: python scripts/pb_schema_asientos_v31.py
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

# Mismos defaults que app/vuelos/services/asientos_service.py — si se
# cambian aquí, cambiarlos también ahí (o mejor: no cambiarlos aquí, este
# script solo siembra la primera vez).
DEFAULT_RECARGO_PREMIUM = "15"
DEFAULT_PCT_FILAS_PREMIUM = "0.15"
DEFAULT_HORAS_CHECKIN_GRATIS = "36"


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def get_collection(headers: dict, name: str) -> dict:
    resp = httpx.get(f"{PB_URL}/api/collections/{name}", headers=headers, timeout=10)
    resp.raise_for_status()
    c = resp.json()
    c["schema"] = c.get("schema", c.get("fields"))
    return c


def ensure_fields(headers: dict, collection: dict, nuevos_campos: list[dict]) -> None:
    existentes = {f["name"] for f in collection["schema"]}
    faltantes = [f for f in nuevos_campos if f["name"] not in existentes]
    if not faltantes:
        print(f"  = {collection['name']}: campos ya presentes, se omite")
        return
    schema_actualizado = collection["schema"] + faltantes
    resp = httpx.patch(
        f"{PB_URL}/api/collections/{collection['id']}",
        json={"schema": schema_actualizado},
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        print(f"  ! error agregando campos a {collection['name']}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    print(f"  + {collection['name']}: agregados {[f['name'] for f in faltantes]}")


def bool_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "bool", "required": required, "options": {}}


def main() -> None:
    headers = {"Authorization": admin_token()}

    print("Actualizando niveles_tarifa...")
    niveles_tarifa = get_collection(headers, "niveles_tarifa")
    ensure_fields(headers, niveles_tarifa, [bool_field("seleccion_asiento_temprana")])

    print("Sembrando seleccion_asiento_temprana por nivel...")
    resp = httpx.get(
        f"{PB_URL}/api/collections/niveles_tarifa/records",
        headers=headers, params={"perPage": 50}, timeout=10,
    )
    resp.raise_for_status()
    # RN confirmada (vuelos-spec.md, RF-VUE-012): Standard/Flex permiten
    # elegir asiento estándar desde el momento de la reserva; Light solo
    # cuando abre el check-in gratuito (o pagando un asiento premium antes).
    habilitados = {"Standard", "Flex"}
    for nivel in resp.json()["items"]:
        deseado = nivel["nombre"] in habilitados
        if nivel.get("seleccion_asiento_temprana") == deseado:
            print(f"  = {nivel['nombre']}: ya en {deseado}, se omite")
            continue
        patch = httpx.patch(
            f"{PB_URL}/api/collections/niveles_tarifa/records/{nivel['id']}",
            json={"seleccion_asiento_temprana": deseado},
            headers=headers, timeout=10,
        )
        patch.raise_for_status()
        print(f"  + {nivel['nombre']}: seleccion_asiento_temprana={deseado}")

    print("Sembrando configuracion_sistema.disponibilidad_asientos...")
    admin_resp = httpx.get(
        f"{PB_URL}/api/collections/usuarios/records",
        headers=headers, params={"filter": f'email="{PB_EMAIL}"'}, timeout=10,
    )
    admin_resp.raise_for_status()
    admins = admin_resp.json()["items"]
    if not admins:
        print("  ! no se encontró el usuario administrador en 'usuarios' — se omite el seed de config", file=sys.stderr)
        return
    modificado_por = admins[0]["id"]

    filas = [
        ("disponibilidad_asientos.recargo_premium", DEFAULT_RECARGO_PREMIUM,
         "Recargo de un asiento premium (salida de emergencia/extra legroom/primeras filas) — RF-VUE-T04, default hasta que CU-T39 tenga UI"),
        ("disponibilidad_asientos.pct_filas_premium", DEFAULT_PCT_FILAS_PREMIUM,
         "Proporción de filas marcadas premium al generar el mapa de asientos — RF-VUE-T04, default hasta que CU-T39 tenga UI"),
        ("disponibilidad_asientos.horas_antes_checkin_gratis", DEFAULT_HORAS_CHECKIN_GRATIS,
         "Horas antes del vuelo en que se habilita la selección gratuita de asiento estándar en tarifa Light — RF-VUE-T05, default hasta que CU-T40 tenga UI"),
    ]
    for clave, valor, descripcion in filas:
        existente = httpx.get(
            f"{PB_URL}/api/collections/configuracion_sistema/records",
            headers=headers, params={"filter": f'clave="{clave}"'}, timeout=10,
        )
        existente.raise_for_status()
        if existente.json()["items"]:
            print(f"  = {clave}: ya existe, se omite")
            continue
        creado = httpx.post(
            f"{PB_URL}/api/collections/configuracion_sistema/records",
            json={
                "clave": clave,
                "valor": valor,
                "categoria": "disponibilidad_asientos",
                "descripcion": descripcion,
                "modificado_por": modificado_por,
            },
            headers=headers, timeout=10,
        )
        if creado.status_code >= 400:
            print(f"  ! error creando {clave}: {creado.text}", file=sys.stderr)
            creado.raise_for_status()
        print(f"  + {clave} = {valor}")

    print("Listo.")


if __name__ == "__main__":
    main()
