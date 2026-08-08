"""Seed idempotente: módulo `estrategico` (nivel estratégico, DS-00 a DS-03
+ configuración de KPIs manuales como CAC digital) — solo accesible para
`Administrador` (el "admin_general" que describe
docs/aerotrack-travel-dashboards-spec.md sección 4 no existe como rol
literal en el sistema real; `Administrador` es el rol que hoy tiene
Nivel 1 sin restricción de Nivel 2 en el módulo `dashboards`, mismo
criterio que se replica acá — ver `seed_dashboards_rbac.py::MATRIZ_ROLES`).

Mismo patrón que `seed_dashboards_rbac.py`: additive, nunca usa PUT con
payload parcial (memoria del proyecto: vacía la matriz de permisos).

Uso: python scripts/seed_estrategico_rbac.py
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ.get("PB_TRAVEL_URL", "http://localhost:8091")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

ROLES_CON_ACCESO = ["Administrador"]


def _get_or_create_modulo(c: httpx.Client, headers: dict) -> str:
    existentes = c.get("/api/collections/modulos/records", params={"filter": 'clave="estrategico"'}, headers=headers).json()["items"]
    if existentes:
        print(f"[modulo] estrategico ya existe: {existentes[0]['id']}")
        return existentes[0]["id"]
    modulo = c.post(
        "/api/collections/modulos/records",
        json={"clave": "estrategico", "nombre_display": "Nivel Estratégico", "descripcion": "Dashboards DS-00 a DS-03 y KPIs manuales (ej. CAC digital)", "orden": 121},
        headers=headers,
    ).raise_for_status().json()
    print(f"[modulo] estrategico creado: {modulo['id']}")
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
        permiso_editar_id = _get_or_create_permiso(c, headers, modulo_id, "editar")

        roles = c.get("/api/collections/roles/records", params={"perPage": 200}, headers=headers).json()["items"]
        rol_id_por_nombre = {r["nombre"]: r["id"] for r in roles}

        rp_existentes = c.get(
            "/api/collections/roles_permisos/records",
            params={"filter": f'permiso_id="{permiso_ver_id}" || permiso_id="{permiso_editar_id}"', "perPage": 500},
            headers=headers,
        ).json()["items"]
        pares_rp = {(rp["rol_id"], rp["permiso_id"]) for rp in rp_existentes}

        for nombre_rol in ROLES_CON_ACCESO:
            rol_id = rol_id_por_nombre.get(nombre_rol)
            if not rol_id:
                print(f"[AVISO] rol {nombre_rol!r} no encontrado, se salta")
                continue
            for permiso_id in (permiso_ver_id, permiso_editar_id):
                if (rol_id, permiso_id) in pares_rp:
                    continue
                c.post("/api/collections/roles_permisos/records", json={"rol_id": rol_id, "permiso_id": permiso_id}, headers=headers).raise_for_status()
                print(f"[roles_permisos] {nombre_rol} -> {permiso_id}")
                pares_rp.add((rol_id, permiso_id))

        print("\nListo.")


if __name__ == "__main__":
    main()
