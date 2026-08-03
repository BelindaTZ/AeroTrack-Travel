"""Agrega `roles_permisos_tablas.accion` — Nivel 2 pasa de restringir por
tabla completa a restringir por (tabla, accion). Antes una sola fila
`(rol, modulo, tabla)` bloqueaba TODAS las acciones sobre esa tabla; ahora
cada acción necesita su propia fila, lo que permite ajustar Nivel 2 más
fino que Nivel 1 (p. ej. "ver" abierto a varias tablas de Facturación pero
"editar" restringido a una sola). Solo "ver"/"crear"/"editar"/"eliminar"
tienen sentido a nivel de fila de tabla — "ejecutar"/"exportar" quedan
exclusivos de Nivel 1 (módulo).

Backfill: las filas ya sembradas (una sola, `scripts/seed_centro_ayuda_rbac.py`
→ Agente/casos_escalados) no tienen accion — se completan con "ver" y se
duplican también a "editar", igualando el alcance que tenían antes de este
cambio (bloqueaban toda acción, no solo una). Ver `seed_centro_ayuda_rbac.py`,
que ya quedó actualizado para sembrar ambas filas en instalaciones nuevas.

Idempotente: no falla si el campo ya existe ni si el backfill ya se hizo.

Ejecutar: python scripts/pb_schema_seguridad_fix_nivel2_accion.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

ACCIONES_NIVEL2 = ["ver", "crear", "editar", "eliminar"]


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def main() -> None:
    headers = {"Authorization": admin_token()}
    resp = httpx.get(f"{PB_URL}/api/collections/roles_permisos_tablas", headers=headers, timeout=10)
    resp.raise_for_status()
    coleccion = resp.json()
    schema = coleccion.get("schema", coleccion.get("fields"))

    if any(f["name"] == "accion" for f in schema):
        print("= roles_permisos_tablas.accion ya existe, nada que hacer")
    else:
        schema.append(
            {
                "name": "accion",
                "type": "select",
                "required": True,
                "options": {"maxSelect": 1, "values": ACCIONES_NIVEL2},
            }
        )
        patch = httpx.patch(
            f"{PB_URL}/api/collections/{coleccion['id']}",
            json={"schema": schema},
            headers=headers,
            timeout=10,
        )
        patch.raise_for_status()
        print(f"+ roles_permisos_tablas.accion creado (select, required, {ACCIONES_NIVEL2})")

    registros = httpx.get(
        f"{PB_URL}/api/collections/roles_permisos_tablas/records",
        params={"perPage": 200},
        headers=headers,
        timeout=10,
    )
    registros.raise_for_status()
    sin_accion = [r for r in registros.json()["items"] if not r.get("accion")]
    if not sin_accion:
        print("= no hay filas sin accion, nada para backfillear")
        return

    for fila in sin_accion:
        # Fila original bloqueaba toda accion sobre la tabla — se reescribe
        # a "ver" y se clona a "editar" para conservar el mismo alcance.
        update = httpx.patch(
            f"{PB_URL}/api/collections/roles_permisos_tablas/records/{fila['id']}",
            json={"accion": "ver"},
            headers=headers,
            timeout=10,
        )
        update.raise_for_status()
        print(f"~ fila {fila['id']} ({fila['tabla']}) -> accion=ver")

        clon = httpx.post(
            f"{PB_URL}/api/collections/roles_permisos_tablas/records",
            json={
                "rol_id": fila["rol_id"],
                "modulo_id": fila["modulo_id"],
                "tabla": fila["tabla"],
                "accion": "editar",
            },
            headers=headers,
            timeout=10,
        )
        clon.raise_for_status()
        print(f"+ fila clonada ({fila['tabla']}) -> accion=editar")


if __name__ == "__main__":
    main()
