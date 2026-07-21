"""Migra el módulo Facturación al esquema v3: pago diferido (CU-O86),
comisiones/remesas polimórficas por tipo_producto (ya no solo vuelo vía
`aerolineas`), reembolso parcial por línea de reserva, conversión de moneda
(CU-O85).

Mismo criterio aditivo que scripts/pb_schema_reservas_v3.py: `comisiones` y
`remesas` MANTIENEN `reserva_id`/`aerolinea_id` required=True tal como están
— el código actual (router_backoffice.py, tests) todavía las escribe así.
Se agregan `reserva_item_id`/`tipo_producto`/`naviera_id`/
`proveedor_comercial_id` en paralelo, sin requerirlos, para que Hoteles/
Autos/Actividades/Cruceros puedan generar comisión real una vez tengan
código propio, sin romper lo que ya factura Vuelos hoy. Migrar el código
para que escriba ambos (o solo los nuevos) es trabajo pendiente, no de esta
migración de esquema.

Cambios:
- `pagos`: +captura_diferida, +fecha_autorizacion; +'autorizado' en estado.
- `comisiones`: +reserva_item_id, +tipo_producto, +naviera_id,
  +proveedor_comercial_id.
- `remesas`: +tipo_producto, +naviera_id, +proveedor_comercial_id.
- `reembolsos`: +reserva_item_id (nullable = reembolso de toda la reserva).
- `facturas.numero_factura`: unique=true (verificado sin duplicados en las
  5 facturas reales existentes).
- NUEVA `tasas_cambio` (CU-O85).

Idempotente en todas sus partes.

Ejecutar: python scripts/pb_schema_facturacion_v3.py
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


def select_field(name: str, values: list[str], required: bool = False) -> dict:
    return {"name": name, "type": "select", "required": required, "options": {"maxSelect": 1, "values": values}}


def relation_field(name: str, target_collection_id: str, required: bool = False) -> dict:
    return {
        "name": name,
        "type": "relation",
        "required": required,
        "options": {"collectionId": target_collection_id, "cascadeDelete": False, "maxSelect": 1},
    }


LOCKED_RULES = {
    "listRule": None,
    "viewRule": None,
    "createRule": None,
    "updateRule": None,
    "deleteRule": None,
}

TIPOS_PRODUCTO = ["vuelo", "hotel", "auto", "actividad", "crucero"]


def main() -> None:
    headers = {"Authorization": admin_token()}
    cache = existing_collections(headers)

    for dep in ("pagos", "comisiones", "remesas", "reembolsos", "facturas", "reserva_items", "navieras", "proveedores_comerciales"):
        if dep not in cache:
            print(f"! falta la colección '{dep}' — no se puede continuar", file=sys.stderr)
            sys.exit(1)

    print("Actualizando pagos...")
    pagos = get_collection(headers, "pagos")
    ensure_fields(headers, pagos, [bool_field("captura_diferida"), date_field("fecha_autorizacion")])
    pagos = get_collection(headers, "pagos")
    ensure_select_values(headers, pagos, "estado", ["autorizado"])

    print("Actualizando comisiones...")
    comisiones = get_collection(headers, "comisiones")
    ensure_fields(
        headers,
        comisiones,
        [
            relation_field("reserva_item_id", cache["reserva_items"]["id"]),
            select_field("tipo_producto", TIPOS_PRODUCTO),
            relation_field("naviera_id", cache["navieras"]["id"]),
            relation_field("proveedor_comercial_id", cache["proveedores_comerciales"]["id"]),
        ],
    )

    print("Actualizando remesas...")
    remesas = get_collection(headers, "remesas")
    ensure_fields(
        headers,
        remesas,
        [
            select_field("tipo_producto", TIPOS_PRODUCTO),
            relation_field("naviera_id", cache["navieras"]["id"]),
            relation_field("proveedor_comercial_id", cache["proveedores_comerciales"]["id"]),
        ],
    )

    print("Actualizando reembolsos...")
    reembolsos = get_collection(headers, "reembolsos")
    ensure_fields(headers, reembolsos, [relation_field("reserva_item_id", cache["reserva_items"]["id"])])

    print("Actualizando facturas...")
    facturas = get_collection(headers, "facturas")
    ensure_unique(headers, facturas, "numero_factura")

    print("Creando tasas_cambio...")
    ensure_collection(
        headers,
        {
            "name": "tasas_cambio",
            "type": "base",
            "schema": [
                text_field("moneda_origen", required=True),
                text_field("moneda_destino", required=True),
                number_field("tasa", required=True),
                date_field("fecha_actualizacion", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
