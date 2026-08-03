"""WP-10 (auditoría de WorkPanels, 2026-07-31) — siembra idempotente del
módulo RBAC "proveedores" (panel de `proveedores_comerciales`, antes sin
ningún router) y lo otorga a Administrador y admin_ventas.

De paso corrige un hallazgo colateral: el módulo "paquetes" (CU-T14,
`scripts/seed_roles_departamento.py`) nunca le otorgó explícitamente
`paquetes.ver`/`paquetes.editar` a Administrador — a diferencia del caso
gemelo `disrupciones.editar`, que sí lo hizo. Confirmado en vivo: con solo
el rol de sistema "Administrador", `/backoffice/paquetes` devolvía 403.
Mismo fix, mismo patrón, mismo script.

Ejecutar: python scripts/seed_proveedores_rbac.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

MODULO_PROVEEDORES = ("proveedores", "Proveedores comerciales", "Catálogo de comisión pactada y contacto por proveedor", 95)
ACCIONES_PROVEEDORES = ("ver", "crear", "editar")


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
    if resp.status_code >= 400:
        print(f"  ! error creando en {collection}: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    headers = {"Authorization": admin_token()}

    # ── módulo "proveedores" ─────────────────────────────────────────
    clave, nombre, descripcion, orden = MODULO_PROVEEDORES
    modulo = get_first(headers, "modulos", f'clave="{clave}"')
    if modulo is None:
        modulo = create(
            headers, "modulos",
            {"clave": clave, "nombre_display": nombre, "descripcion": descripcion, "orden": orden},
        )
        print(f"+ modulo {clave}")
    else:
        print(f"= modulo {clave} ya existe")

    ya_tiene_tabla = any(
        mt["modulo_id"] == modulo["id"] and mt["tabla"] == "proveedores_comerciales"
        for mt in get_all(headers, "modulo_tablas")
    )
    if ya_tiene_tabla:
        print("= modulo_tablas proveedores.proveedores_comerciales ya existe")
    else:
        create(
            headers, "modulo_tablas",
            {"modulo_id": modulo["id"], "tabla": "proveedores_comerciales",
             "descripcion": "Tabla 'proveedores_comerciales' del módulo proveedores"},
        )
        print("+ modulo_tablas proveedores.proveedores_comerciales")

    permisos_por_accion: dict[str, dict] = {
        p["accion"]: p for p in get_all(headers, "permisos") if p["modulo_id"] == modulo["id"]
    }
    for accion in ACCIONES_PROVEEDORES:
        if accion in permisos_por_accion:
            print(f"= permiso proveedores.{accion} ya existe")
            continue
        permisos_por_accion[accion] = create(headers, "permisos", {"modulo_id": modulo["id"], "accion": accion})
        print(f"+ permiso proveedores.{accion}")

    roles_por_nombre = {r["nombre"]: r for r in get_all(headers, "roles")}
    roles_permisos_existentes = {(rp["rol_id"], rp["permiso_id"]) for rp in get_all(headers, "roles_permisos")}

    def otorgar(rol_nombre: str, permiso_id: str, etiqueta: str) -> None:
        rol = roles_por_nombre.get(rol_nombre)
        if rol is None:
            print(f"  ! rol '{rol_nombre}' no encontrado — saltando {etiqueta}")
            return
        key = (rol["id"], permiso_id)
        if key in roles_permisos_existentes:
            return
        create(headers, "roles_permisos", {"rol_id": rol["id"], "permiso_id": permiso_id})
        roles_permisos_existentes.add(key)
        print(f"+ roles_permisos {etiqueta}")

    for rol_nombre in ("Administrador", "admin_ventas"):
        for accion in ACCIONES_PROVEEDORES:
            otorgar(rol_nombre, permisos_por_accion[accion]["id"], f"{rol_nombre} -> proveedores.{accion}")

    # ── fix colateral: Administrador nunca tuvo paquetes.ver/editar ────
    modulo_paquetes = get_first(headers, "modulos", 'clave="paquetes"')
    if modulo_paquetes is None:
        print("  ! módulo 'paquetes' no encontrado — saltando fix colateral")
    else:
        permisos_paquetes = {
            p["accion"]: p for p in get_all(headers, "permisos") if p["modulo_id"] == modulo_paquetes["id"]
        }
        for accion in ("ver", "editar"):
            permiso = permisos_paquetes.get(accion)
            if permiso is None:
                print(f"  ! permiso paquetes.{accion} no encontrado — saltando")
                continue
            otorgar("Administrador", permiso["id"], f"Administrador -> paquetes.{accion} (fix colateral WP-10)")

    print("Listo.")


if __name__ == "__main__":
    main()
