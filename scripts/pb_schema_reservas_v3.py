"""Migra el módulo Reservas al esquema v3 — el cambio estructural más
grande de la propuesta (docs/aerotrack-travel-propuesta-tablas-v3.dbml,
sección "Reservas — REDISEÑO").

DECISIÓN DE ALCANCE para esta migración de esquema (no de código):
`reservas.vuelo_id`/`tarifa_id` NO se tocan ni se marcan opcionales aquí.
El dbml v3 los elimina porque el producto reservado pasa a vivir en la
nueva `reserva_items` (polimórfica), pero `app/reservas/repositories/
reservas_repo.py` todavía lee `vuelo_id` directo sobre `reservas` — quitar
esos campos ahora rompería el código actual sin haber migrado los datos de
las 9 reservas existentes a `reserva_items` ni actualizado el repositorio.
Esta migración solo AGREGA lo nuevo (aditivo, cero riesgo para lo que ya
funciona); la migración de datos + repositorio es trabajo de código
pendiente, no de esquema — ver specs/operativo/reservas/tasks.md.

Cambios aplicados:
- `reservas`: +es_paquete, +descuento_paquete_pct, +voucher_pdf (file);
  `codigo_reserva` pasa a unique=true (verificado sin duplicados en las
  9 reservas reales existentes antes de aplicar).
- NUEVA `reserva_items` (el corazón del rediseño, polimórfica por
  tipo_producto).
- `reserva_pasajeros`: +asiento_id (relation real a asientos_vuelo) y
  +asiento_asignado_por; el campo `asiento` (texto libre) queda tal cual,
  deprecado sin borrar (ninguna fila real lo usa todavía porque
  asientos_vuelo no existía hasta la migración de Vuelos de hoy).
- `reserva_extras.tipo`: se agrega el valor 'traslado_aeropuerto' que
  faltaba (dbml v3 lo agrega al enum tipo_extra).
- NUEVA `requisitos_visa_cache` (CU-O81).

Idempotente en todas sus partes.

Ejecutar: python scripts/pb_schema_reservas_v3.py
"""

import os
import sys

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


def existing_collections(headers: dict) -> dict[str, dict]:
    resp = httpx.get(f"{PB_URL}/api/collections", params={"perPage": 200}, headers=headers, timeout=10)
    resp.raise_for_status()
    return {c["name"]: c for c in resp.json()["items"]}


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


def ensure_select_values(headers: dict, collection: dict, campo: str, valores_nuevos: list[str]) -> None:
    f = next(x for x in collection["schema"] if x["name"] == campo)
    actuales = f["options"]["values"]
    faltantes = [v for v in valores_nuevos if v not in actuales]
    if not faltantes:
        print(f"  = {collection['name']}.{campo}: valores ya presentes, se omite")
        return
    vistos: list[str] = []
    for v in actuales + faltantes:
        if v not in vistos:
            vistos.append(v)
    f["options"]["values"] = vistos
    resp = httpx.patch(
        f"{PB_URL}/api/collections/{collection['id']}",
        json={"schema": collection["schema"]},
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        print(f"  ! error agregando valores a {collection['name']}.{campo}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    print(f"  + {collection['name']}.{campo}: agregados valores {faltantes}")


def ensure_unique(headers: dict, collection: dict, campo: str) -> None:
    f = next(x for x in collection["schema"] if x["name"] == campo)
    if f.get("unique"):
        print(f"  = {collection['name']}.{campo}: ya es unique=true, se omite")
        return
    f["unique"] = True
    resp = httpx.patch(
        f"{PB_URL}/api/collections/{collection['id']}",
        json={"schema": collection["schema"]},
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        print(f"  ! error marcando {collection['name']}.{campo} unique: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    print(f"  + {collection['name']}.{campo}: ahora unique=true")


def ensure_collection(headers: dict, payload: dict, cache: dict[str, dict]) -> dict:
    name = payload["name"]
    if name in cache:
        print(f"  = {name} ya existe, se omite")
        return cache[name]
    resp = httpx.post(f"{PB_URL}/api/collections", json=payload, headers=headers, timeout=10)
    if resp.status_code >= 400:
        print(f"  ! error creando {name}: {resp.status_code} {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    created = resp.json()
    cache[name] = created
    print(f"  + {name} creada (id={created['id']})")
    return created


def text_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "text", "required": required, "options": {}}


def number_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "number", "required": required, "options": {}}


def bool_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "bool", "required": required, "options": {}}


def date_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "date", "required": required, "options": {}}


def json_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "json", "required": required, "options": {"maxSize": 2000000}}


def select_field(name: str, values: list[str], required: bool = False) -> dict:
    return {"name": name, "type": "select", "required": required, "options": {"maxSelect": 1, "values": values}}


def relation_field(name: str, target_collection_id: str, required: bool = False) -> dict:
    return {
        "name": name,
        "type": "relation",
        "required": required,
        "options": {"collectionId": target_collection_id, "cascadeDelete": False, "maxSelect": 1},
    }


def file_field(name: str, mime_types: list[str], max_size: int = 5242880) -> dict:
    return {
        "name": name,
        "type": "file",
        "required": False,
        "options": {"maxSelect": 1, "maxSize": max_size, "mimeTypes": mime_types},
    }


LOCKED_RULES = {
    "listRule": None,
    "viewRule": None,
    "createRule": None,
    "updateRule": None,
    "deleteRule": None,
}

TIPOS_PRODUCTO = ["vuelo", "hotel", "auto", "actividad", "crucero"]


def reserva_item_producto_fields() -> list[dict]:
    """Campos polimórficos compartidos por reserva_items y carrito_items —
    solo se llena el par correspondiente al tipo_producto de la fila."""
    return [
        text_field("vuelo_id"),
        text_field("tarifa_vuelo_id"),
        text_field("hotel_id"),
        text_field("hotel_tarifa_id"),
        text_field("auto_id"),
        text_field("actividad_id"),
        text_field("actividad_horario_id"),
        text_field("crucero_id"),
        text_field("crucero_camarote_id"),
    ]


def main() -> None:
    headers = {"Authorization": admin_token()}
    cache = existing_collections(headers)

    for dep in ("reservas", "reserva_pasajeros", "reserva_extras", "asientos_vuelo"):
        if dep not in cache:
            print(f"! falta la colección '{dep}' — no se puede continuar", file=sys.stderr)
            sys.exit(1)

    print("Actualizando reservas...")
    reservas = get_collection(headers, "reservas")
    ensure_fields(
        headers,
        reservas,
        [
            bool_field("es_paquete"),
            number_field("descuento_paquete_pct"),
            file_field("voucher_pdf", ["application/pdf"]),
        ],
    )
    reservas = get_collection(headers, "reservas")
    ensure_unique(headers, reservas, "codigo_reserva")

    print("Creando reserva_items (polimórfica)...")
    reserva_items = ensure_collection(
        headers,
        {
            "name": "reserva_items",
            "type": "base",
            "schema": [
                relation_field("reserva_id", reservas["id"], required=True),
                select_field("tipo_producto", TIPOS_PRODUCTO, required=True),
                *reserva_item_producto_fields(),
                select_field("modalidad_pago", ["pagar_ahora", "pagar_al_recoger", "pago_diferido"]),
                date_field("fecha_inicio"),
                date_field("fecha_fin"),
                number_field("precio_final", required=True),
                select_field(
                    "estado_item",
                    ["pendiente", "confirmado", "modificado", "cancelado", "completado"],
                    required=True,
                ),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Actualizando reserva_pasajeros...")
    reserva_pasajeros = get_collection(headers, "reserva_pasajeros")
    ensure_fields(
        headers,
        reserva_pasajeros,
        [
            relation_field("asiento_id", cache["asientos_vuelo"]["id"]),
            select_field("asiento_asignado_por", ["pasajero", "sistema"]),
        ],
    )

    print("Actualizando reserva_extras...")
    reserva_extras = get_collection(headers, "reserva_extras")
    ensure_select_values(headers, reserva_extras, "tipo", ["traslado_aeropuerto"])

    print("Creando requisitos_visa_cache...")
    ensure_collection(
        headers,
        {
            "name": "requisitos_visa_cache",
            "type": "base",
            "schema": [
                text_field("pasaporte_pais", required=True),
                text_field("destino_pais", required=True),
                json_field("resultado", required=True),
                date_field("fecha_consulta", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")
    print(f"(reserva_items id={reserva_items['id']}, para referencia de otros scripts)")


if __name__ == "__main__":
    main()
