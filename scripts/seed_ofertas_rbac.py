"""Siembra idempotente del RBAC de Ofertas y Promociones (CU-T30/T31/T32/T44):
`modulos`, `permisos` (ver/crear/editar), `roles_permisos` solo para
Administrador — el catálogo dice explícitamente "Actor: Administrador"
para las 4 funcionalidades tácticas de este módulo, sin rol Agente
involucrado (a diferencia de Centro de Ayuda). Mismo patrón de upsert que
`seed_integraciones_rbac.py`.

Requiere que `seed_seguridad.py` ya haya corrido (rol "Administrador"
sembrado).

Ejecutar: python scripts/seed_ofertas_rbac.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

MODULO_CLAVE = "ofertas"
ACCIONES = ["ver", "crear", "editar"]
TABLAS = ["ofertas_destacadas", "cupones_descuento", "cupones_uso", "campanas_email", "newsletter_suscripciones"]


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def get_all(headers: dict, collection: str) -> list[dict]:
    resp = httpx.get(
        f"{PB_URL}/api/collections/{collection}/records", params={"perPage": 200}, headers=headers, timeout=10
    )
    resp.raise_for_status()
    return resp.json()["items"]


def get_first(headers: dict, collection: str, filtro: str) -> dict | None:
    resp = httpx.get(
        f"{PB_URL}/api/collections/{collection}/records",
        params={"perPage": 1, "filter": filtro},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json()["items"]
    return items[0] if items else None


def create(headers: dict, collection: str, data: dict) -> dict:
    resp = httpx.post(f"{PB_URL}/api/collections/{collection}/records", json=data, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    headers = {"Authorization": admin_token()}

    modulo = get_first(headers, "modulos", f'clave="{MODULO_CLAVE}"')
    if modulo is None:
        modulo = create(
            headers, "modulos",
            {
                "clave": MODULO_CLAVE, "nombre_display": "Ofertas y Promociones",
                "descripcion": "Ofertas destacadas, cupones, campañas de email y acumulación con paquetes (CU-T30/T31/T32/T44)",
                "orden": 100,
            },
        )
        print(f"+ modulo {MODULO_CLAVE}")
    else:
        print(f"= modulo {MODULO_CLAVE} ya existe")

    rol_admin = get_first(headers, "roles", 'nombre="Administrador"')
    if rol_admin is None:
        raise RuntimeError("Rol Administrador no sembrado — correr scripts/seed_seguridad.py primero")

    permisos_existentes = {p["accion"]: p for p in get_all(headers, "permisos") if p["modulo_id"] == modulo["id"]}
    roles_permisos_existentes = {
        rp["permiso_id"] for rp in get_all(headers, "roles_permisos") if rp["rol_id"] == rol_admin["id"]
    }
    for accion in ACCIONES:
        permiso = permisos_existentes.get(accion)
        if permiso is None:
            permiso = create(headers, "permisos", {"modulo_id": modulo["id"], "accion": accion})
            permisos_existentes[accion] = permiso
            print(f"+ permiso {MODULO_CLAVE}.{accion}")
        if permiso["id"] not in roles_permisos_existentes:
            create(headers, "roles_permisos", {"rol_id": rol_admin["id"], "permiso_id": permiso["id"]})
            roles_permisos_existentes.add(permiso["id"])
            print(f"+ roles_permisos Administrador -> {MODULO_CLAVE}.{accion}")

    modulo_tablas_existentes = {
        mt["tabla"] for mt in get_all(headers, "modulo_tablas") if mt["modulo_id"] == modulo["id"]
    }
    for tabla in TABLAS:
        if tabla in modulo_tablas_existentes:
            continue
        create(
            headers, "modulo_tablas",
            {"modulo_id": modulo["id"], "tabla": tabla, "descripcion": f"Tabla '{tabla}' del módulo {MODULO_CLAVE}"},
        )
        print(f"+ modulo_tablas {MODULO_CLAVE}.{tabla}")

    print("Listo.")


if __name__ == "__main__":
    main()
