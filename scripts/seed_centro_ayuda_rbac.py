"""Siembra idempotente del RBAC de Centro de Ayuda (CU-T28/T29/T36):
`modulos`, `permisos` (ver/crear/editar), `roles_permisos` para
Administrador (acceso total: artículos + métricas + casos) y Agente
(solo casos escalados), y una restricción Nivel 2
(`roles_permisos_tablas`) que limita a Agente a la tabla
`casos_escalados` — sin esa fila, Agente heredaría acceso de Nivel 1 al
módulo completo, incluida la gestión de artículos (CU-T28), que el
catálogo reserva a Administrador. Mismo patrón de upsert que
`seed_integraciones_rbac.py`.

Requiere que `seed_seguridad.py` ya haya corrido (roles "Administrador"
y "Agente" sembrados).

Ejecutar: python scripts/seed_centro_ayuda_rbac.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

MODULO_CLAVE = "centro_ayuda"
ACCIONES = ["ver", "crear", "editar"]
TABLAS = ["articulos_ayuda", "articulo_calificaciones", "casos_escalados"]


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


def otorgar(headers: dict, rol: dict, permiso: dict, roles_permisos_existentes: set) -> None:
    if permiso["id"] not in roles_permisos_existentes:
        create(headers, "roles_permisos", {"rol_id": rol["id"], "permiso_id": permiso["id"]})
        roles_permisos_existentes.add(permiso["id"])
        print(f"+ roles_permisos {rol['nombre']} -> {MODULO_CLAVE}.{permiso['accion']}")


def main() -> None:
    headers = {"Authorization": admin_token()}

    modulo = get_first(headers, "modulos", f'clave="{MODULO_CLAVE}"')
    if modulo is None:
        modulo = create(
            headers, "modulos",
            {
                "clave": MODULO_CLAVE, "nombre_display": "Centro de Ayuda",
                "descripcion": "Base de conocimiento, calificaciones y casos escalados (CU-T28/T29/T36)",
                "orden": 90,
            },
        )
        print(f"+ modulo {MODULO_CLAVE}")
    else:
        print(f"= modulo {MODULO_CLAVE} ya existe")

    rol_admin = get_first(headers, "roles", 'nombre="Administrador"')
    rol_agente = get_first(headers, "roles", 'nombre="Agente"')
    if rol_admin is None or rol_agente is None:
        raise RuntimeError("Roles Administrador/Agente no sembrados — correr scripts/seed_seguridad.py primero")

    permisos_existentes = {p["accion"]: p for p in get_all(headers, "permisos") if p["modulo_id"] == modulo["id"]}
    for accion in ACCIONES:
        if accion not in permisos_existentes:
            permiso = create(headers, "permisos", {"modulo_id": modulo["id"], "accion": accion})
            permisos_existentes[accion] = permiso
            print(f"+ permiso {MODULO_CLAVE}.{accion}")

    rp_admin = {rp["permiso_id"] for rp in get_all(headers, "roles_permisos") if rp["rol_id"] == rol_admin["id"]}
    for accion in ACCIONES:
        otorgar(headers, rol_admin, {**permisos_existentes[accion], "accion": accion}, rp_admin)

    rp_agente = {rp["permiso_id"] for rp in get_all(headers, "roles_permisos") if rp["rol_id"] == rol_agente["id"]}
    for accion in ("ver", "editar"):
        otorgar(headers, rol_agente, {**permisos_existentes[accion], "accion": accion}, rp_agente)

    # Una fila por accion (RN-SEG-009 extendida a nivel de tabla, 2026-07-30):
    # Nivel 2 ahora restringe por (tabla, accion), no solo por tabla — hay que
    # sembrar "ver" y "editar" (las dos acciones Nivel 1 de Agente en este
    # módulo) para que la restricción a casos_escalados cubra todo lo que
    # antes cubría una sola fila sin accion.
    restricciones_agente = get_all(headers, "roles_permisos_tablas")
    for accion in ("ver", "editar"):
        ya_restringido = any(
            r["rol_id"] == rol_agente["id"] and r["modulo_id"] == modulo["id"]
            and r["tabla"] == "casos_escalados" and r.get("accion") == accion
            for r in restricciones_agente
        )
        if not ya_restringido:
            create(
                headers, "roles_permisos_tablas",
                {"rol_id": rol_agente["id"], "modulo_id": modulo["id"], "tabla": "casos_escalados", "accion": accion},
            )
            print(f"+ roles_permisos_tablas Agente -> {MODULO_CLAVE}.casos_escalados.{accion} (Nivel 2)")
        else:
            print(f"= restricción Nivel 2 de Agente ({accion}) ya existe")

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
