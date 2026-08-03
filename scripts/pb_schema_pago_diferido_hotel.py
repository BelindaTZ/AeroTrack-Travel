"""Migración de esquema — Reservar hotel con pago diferido (CU-O60/O86,
RF-HOT-009/RF-FAC-012).

El esquema v3 de Facturación (`pb_schema_facturacion_v3.py`) ya agregó
`pagos.captura_diferida`/`fecha_autorizacion` y el valor `autorizado` en
`pagos.estado`; y `reserva_items.modalidad_pago` (`pb_schema_reservas_v3.py`)
ya incluye `pago_diferido` como valor válido. Lo que falta:

- `carrito_items.modalidad_pago` — el carrito no tenía este campo; sin él,
  la elección del pasajero ("pagar ahora" vs "reservar sin pagar ahora") no
  puede viajar de la selección de tarifa hasta `reserva_items` al hacer
  checkout.
- `hoteles_tarifas.pago_diferido_disponible` (bool) — RN-HOT-004: no todas
  las tarifas de HotelLens admiten pago diferido. HotelLens no expone este
  atributo (no es un dato real de la fuente), así que se deriva de forma
  sintética en `catalogo_service.py`: una tarifa admite pago diferido si
  es `reembolsable` (mismo criterio de riesgo — si se puede cancelar gratis,
  diferir el cobro no expone al negocio a un impago sin cupo bloqueado).

Idempotente.

Ejecutar: python scripts/pb_schema_pago_diferido_hotel.py
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


def select_field(name: str, values: list[str], required: bool = False) -> dict:
    return {"name": name, "type": "select", "required": required, "options": {"maxSelect": 1, "values": values}}


def main() -> None:
    headers = {"Authorization": admin_token()}

    print("Actualizando carrito_items...")
    carrito_items = get_collection(headers, "carrito_items")
    ensure_fields(
        headers, carrito_items,
        [select_field("modalidad_pago", ["pagar_ahora", "pagar_al_recoger", "pago_diferido"])],
    )

    print("Actualizando hoteles_tarifas...")
    hoteles_tarifas = get_collection(headers, "hoteles_tarifas")
    ensure_fields(headers, hoteles_tarifas, [bool_field("pago_diferido_disponible")])

    print("Listo.")


if __name__ == "__main__":
    main()
