"""Migra el módulo Vuelos al esquema v3 (docs/aerotrack-travel-propuesta-
tablas-v3.dbml): agrega campos nuevos a `vuelos_catalogo`/`tarifas_vuelo`
(risk score CU-O52/O83, datos reales de AeroDataBox/Google Flights,
clase_cabina) y crea 2 colecciones nuevas: `asientos_vuelo` (CU-O21/22/23,
mapa real de asientos por vuelo) y `predicciones_precio_ruta` (CU-O51).

Decisiones de compatibilidad con datos existentes:
- `tarifas_vuelo.clase_cabina` se agrega con required=False (no True como
  dice el dbml) — mismo motivo que el bug ya documentado en
  errores-conocidos.md para `cupos_disponibles`: un campo requerido nuevo
  rompe cualquier update futuro sobre las filas ya creadas por el DAG antes
  de este cambio, que no tienen valor. El código nuevo debe escribir
  siempre 'economy' por defecto (RF nuevo, no automático de PocketBase).
- `vuelos_catalogo.generado_por` conserva el valor histórico 'sistema' en
  la lista de opciones (no se borra) y se agregan 'sistema_api_real' /
  'sistema_formula' del dbml v3 — las filas ya generadas por
  catalogo_vuelos_tasks.py usan 'sistema' literal; quitarlo invalidaría
  datos reales ya escritos. Pendiente de código: migrar ese task a escribir
  'sistema_formula' en vez de 'sistema' (no se hace en esta migración de
  esquema, ver specs/operativo/vuelos/tasks.md).

Idempotente en ambas partes (campos y colecciones).

Ejecutar: python scripts/pb_schema_vuelos_v3.py
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
    # dedupe defensivo: una corrida previa pudo haber aplicado el cambio en
    # PocketBase pese a devolver 400 (visto en la práctica con este mismo
    # campo) — nunca enviar duplicados en options.values.
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


LOCKED_RULES = {
    "listRule": None,
    "viewRule": None,
    "createRule": None,
    "updateRule": None,
    "deleteRule": None,
}


def main() -> None:
    headers = {"Authorization": admin_token()}

    print("Actualizando vuelos_catalogo...")
    vuelos_catalogo = get_collection(headers, "vuelos_catalogo")
    ensure_fields(
        headers,
        vuelos_catalogo,
        [
            text_field("avion_icao24"),
            text_field("avion_modelo"),
            number_field("emisiones_co2_kg"),
            text_field("fuente_busqueda_ref"),
            json_field("detalles_extra"),
            number_field("risk_score"),
            text_field("risk_score_fuente"),
            date_field("risk_score_actualizado"),
        ],
    )
    vuelos_catalogo = get_collection(headers, "vuelos_catalogo")  # refrescar tras el patch
    ensure_select_values(headers, vuelos_catalogo, "generado_por", ["sistema_api_real", "sistema_formula"])

    print("Actualizando tarifas_vuelo...")
    tarifas_vuelo = get_collection(headers, "tarifas_vuelo")
    ensure_fields(
        headers,
        tarifas_vuelo,
        [select_field("clase_cabina", ["economy", "premium_economy", "business", "first"], required=False)],
    )

    print("Verificando/creando colecciones nuevas...")
    cache = existing_collections(headers)

    ensure_collection(
        headers,
        {
            "name": "asientos_vuelo",
            "type": "base",
            "schema": [
                relation_field("vuelo_id", vuelos_catalogo["id"], required=True),
                number_field("fila", required=True),
                text_field("columna", required=True),
                select_field("tipo_asiento", ["ventana", "pasillo", "medio"], required=True),
                bool_field("es_premium"),
                number_field("recargo"),
                bool_field("disponible"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "predicciones_precio_ruta",
            "type": "base",
            "schema": [
                text_field("origen_codigo", required=True),
                text_field("destino_codigo", required=True),
                date_field("fecha_objetivo", required=True),
                number_field("precio_minimo_historico"),
                text_field("nivel_precio"),
                number_field("rango_tipico_min"),
                number_field("rango_tipico_max"),
                json_field("historico_precios"),
                number_field("precio_predicho", required=True),
                text_field("tendencia"),
                number_field("confianza"),
                date_field("fecha_calculo", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    print("Listo.")


if __name__ == "__main__":
    main()
