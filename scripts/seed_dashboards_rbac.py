"""Seed idempotente: módulo `dashboards` + RBAC granular por dashboard,
según la matriz de la sección 4 de docs/aerotrack-travel-dashboards-spec.md.

`permisos.accion` es un campo `select` con valores fijos (ver/crear/editar/
eliminar/exportar/ejecutar) — no admite acciones custom tipo "ver_comercial".
Por eso se usa el mecanismo de Nivel 2 YA EXISTENTE en rbac_service.py:
`roles_permisos_tablas` (rol_id, modulo_id, accion, tabla=texto libre) para
la acción "ver" — cada dashboard (DB-01, DB-02, ...) se modela como una
"tabla" dentro del módulo único "dashboards" (comercial, finanzas,
operaciones, clientes, demanda, paquetes, catalogo_rutas, soporte,
campanas, asistente_ia, alertas_precio, agentes).

Un rol con Nivel 1 "ver" en el módulo pero SIN filas en
`roles_permisos_tablas` ve TODOS los dashboards (así queda Administrador) —
comportamiento ya documentado en `tiene_permiso()`.

IMPORTANTE — "exportar" no soporta Nivel 2: el campo `accion` de
`roles_permisos_tablas` en el schema real de PocketBase solo acepta
ver/crear/editar/eliminar (sin "exportar"), así que "exportar" queda
Nivel 1 únicamente (todo o nada por módulo, no por dashboard individual).
El único caso de la matriz que necesitaría esa granularidad es admin_finanzas
en DB-01 (👁 solo lectura, sin exportar, pero SÍ exporta DB-02) — ese caso
puntual se resuelve con un chequeo explícito en el router de DB-01
(comparando el nombre del rol), documentado ahí mismo.

DB-04 (pasajero) no tiene gate acá — es público en /vuelos/buscar, la spec
no lo restringe.

CUIDADO (memoria del proyecto): nunca usar PUT /admin/roles/{id} con
payload parcial — vacía toda la matriz de permisos del rol. Este script
solo hace POST de registros nuevos, additive.

Uso: python scripts/seed_dashboards_rbac.py
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ.get("PB_TRAVEL_URL", "http://localhost:8091")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

TODAS_LAS_TABLAS = [
    "comercial", "finanzas", "operaciones", "clientes", "demanda",
    "paquetes", "catalogo_rutas", "soporte", "campanas", "asistente_ia",
    "alertas_precio", "agentes",
]

# rol -> tablas con "ver" (None = todas, sin restricción Nivel 2).
# "exportar" es Nivel 1 puro (todo o nada): se otorga a todo rol de esta
# lista salvo el caso admin_finanzas/DB-01, resuelto en código (ver docstring).
MATRIZ_ROLES: dict[str, list[str] | None] = {
    "Administrador": None,
    "admin_ventas": ["comercial", "demanda", "paquetes", "catalogo_rutas"],
    "admin_finanzas": ["comercial", "finanzas"],
    "admin_operaciones": ["operaciones", "soporte", "agentes"],
    "admin_clientes": ["clientes", "alertas_precio"],
    "admin_comercial": ["campanas", "asistente_ia"],
    "Agente": ["agentes"],  # propia, filtrada además por agente_id en la query
}


def _get_or_create_modulo(c: httpx.Client, headers: dict) -> str:
    existentes = c.get("/api/collections/modulos/records", params={"filter": 'clave="dashboards"'}, headers=headers).json()["items"]
    if existentes:
        print(f"[modulo] dashboards ya existe: {existentes[0]['id']}")
        return existentes[0]["id"]
    modulo = c.post(
        "/api/collections/modulos/records",
        json={"clave": "dashboards", "nombre_display": "Dashboards", "descripcion": "Informes compuestos y KPIs ejecutivos", "orden": 120},
        headers=headers,
    ).raise_for_status().json()
    print(f"[modulo] dashboards creado: {modulo['id']}")
    return modulo["id"]


def _get_or_create_permiso(c: httpx.Client, headers: dict, modulo_id: str, accion: str) -> str:
    existentes = c.get(
        "/api/collections/permisos/records", params={"filter": f'modulo_id="{modulo_id}" && accion="{accion}"'}, headers=headers
    ).json()["items"]
    if existentes:
        print(f"[permiso] {accion} ya existe: {existentes[0]['id']}")
        return existentes[0]["id"]
    permiso = c.post("/api/collections/permisos/records", json={"modulo_id": modulo_id, "accion": accion}, headers=headers).raise_for_status().json()
    print(f"[permiso] {accion} creado: {permiso['id']}")
    return permiso["id"]


def main() -> None:
    with httpx.Client(base_url=PB_URL, timeout=30) as c:
        token = c.post("/api/admins/auth-with-password", json={"identity": PB_EMAIL, "password": PB_PASSWORD}).raise_for_status().json()["token"]
        headers = {"Authorization": token}

        modulo_id = _get_or_create_modulo(c, headers)
        permiso_ver_id = _get_or_create_permiso(c, headers, modulo_id, "ver")
        permiso_exportar_id = _get_or_create_permiso(c, headers, modulo_id, "exportar")

        roles = c.get("/api/collections/roles/records", params={"perPage": 200}, headers=headers).json()["items"]
        rol_id_por_nombre = {r["nombre"]: r["id"] for r in roles}

        rp_existentes = c.get(
            "/api/collections/roles_permisos/records",
            params={"filter": f'permiso_id="{permiso_ver_id}" || permiso_id="{permiso_exportar_id}"', "perPage": 500},
            headers=headers,
        ).json()["items"]
        pares_rp = {(rp["rol_id"], rp["permiso_id"]) for rp in rp_existentes}

        rpt_existentes = c.get(
            "/api/collections/roles_permisos_tablas/records",
            params={"filter": f'modulo_id="{modulo_id}"', "perPage": 500},
            headers=headers,
        ).json()["items"]
        tripletas_rpt = {(rpt["rol_id"], rpt["accion"], rpt["tabla"]) for rpt in rpt_existentes}

        for nombre_rol, tablas_ver in MATRIZ_ROLES.items():
            rol_id = rol_id_por_nombre.get(nombre_rol)
            if not rol_id:
                print(f"[AVISO] rol {nombre_rol!r} no encontrado, se salta")
                continue

            # Nivel 1 — "ver" y "exportar" en el módulo dashboards
            for permiso_id in (permiso_ver_id, permiso_exportar_id):
                if (rol_id, permiso_id) in pares_rp:
                    continue
                c.post("/api/collections/roles_permisos/records", json={"rol_id": rol_id, "permiso_id": permiso_id}, headers=headers).raise_for_status()
                print(f"[roles_permisos] {nombre_rol} -> nivel1 ok")
                pares_rp.add((rol_id, permiso_id))

            # Nivel 2 — restricciones de tabla para "ver" (None = sin restricción = ve todas)
            if tablas_ver is None:
                continue
            for tabla in tablas_ver:
                if (rol_id, "ver", tabla) in tripletas_rpt:
                    continue
                c.post(
                    "/api/collections/roles_permisos_tablas/records",
                    json={"rol_id": rol_id, "modulo_id": modulo_id, "accion": "ver", "tabla": tabla},
                    headers=headers,
                ).raise_for_status()
                print(f"[roles_permisos_tablas] {nombre_rol} -> ver:{tabla}")
                tripletas_rpt.add((rol_id, "ver", tabla))

        print("\nListo.")


if __name__ == "__main__":
    main()
