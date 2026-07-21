"""Borra los datos de demo/flujo-de-prueba del modelo viejo de reservas
(pre-rediseño v3): 9 `reservas` con `vuelo_id`/`tarifa_id` directos y sus
dependientes (`pagos`, `comisiones`, `facturas`, `notificaciones` con
`reserva_id` poblado). Autorizado explícitamente por el usuario — estos
registros eran solo para ver el flujo funcionando, no datos reales de
clientes.

NO toca: vuelos_catalogo/tarifas_vuelo/aerolineas (catálogo real generado
por el DAG diario), disrupciones (87 filas ligadas a vuelo_id, no a
reserva_id — trabajo operativo real del simulador, no demo de reservas),
pasajeros/usuarios, ni ninguna de las colecciones nuevas del rediseño v3
(reserva_items, carritos, etc. — todas vacías, nada que borrar ahí).

A partir de aquí, las reservas nuevas se crean directamente sobre el
modelo v3 (reserva_items polimórfico), no sobre el modelo viejo que se
está borrando.

Volumen bajo (9/5/5/1 filas) — sin necesidad del patrón de concurrencia
usado para borrados masivos (ver memoria de infraestructura minio-elt).

Ejecutar: python scripts/limpiar_datos_demo_reservas.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

# Orden: hijos antes que padres (evitar relaciones colgantes aunque
# cascadeDelete=False no lo exija estrictamente en PocketBase).
COLECCIONES_EN_ORDEN = ["notificaciones", "facturas", "comisiones", "pagos", "reservas"]


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def borrar_todos(headers: dict, coleccion: str) -> int:
    resp = httpx.get(
        f"{PB_URL}/api/collections/{coleccion}/records",
        params={"perPage": 200, "fields": "id"},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    ids = [item["id"] for item in resp.json()["items"]]
    for rid in ids:
        d = httpx.delete(f"{PB_URL}/api/collections/{coleccion}/records/{rid}", headers=headers, timeout=10)
        if d.status_code >= 400:
            print(f"  ! error borrando {coleccion}/{rid}: {d.status_code} {d.text}")
    print(f"  - {coleccion}: {len(ids)} registros borrados")
    return len(ids)


def main() -> None:
    headers = {"Authorization": admin_token()}
    print("Borrando datos demo del modelo viejo de reservas...")
    total = 0
    for coleccion in COLECCIONES_EN_ORDEN:
        total += borrar_todos(headers, coleccion)
    print(f"Listo. {total} registros borrados en total.")


if __name__ == "__main__":
    main()
