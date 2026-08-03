"""Crea un usuario demo (ficticio) por cada rol de departamento del punto 7
de `docs/aerotrack-travel-cambios-pendientes.md` — para que el usuario final
pueda entrar a cada panel y capturar cada informe nuevo. Idempotente por
email (upsert de contraseña si el usuario ya existe, para no perder acceso
si se corre dos veces).

Ejecutar: python scripts/seed_usuarios_demo_departamento.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

PASSWORD_DEMO = "AeroDemo2026"

# (nombre_completo, email, rol_nombre)
# NOTA 2026-07-27: "admin_general" se eliminó por duplicar "Administrador"
# (mismo acceso total, confuso tener dos) — demo.admingeneral@aerotrack.test
# se reasignó a rol "Administrador" a mano, ya no se crea/gestiona acá.
USUARIOS_DEMO = [
    ("Karla Ibarra (TI)", "demo.adminti@aerotrack.test", "admin_ti"),
    ("Renato Salazar (Finanzas)", "demo.adminfinanzas@aerotrack.test", "admin_finanzas"),
    ("Valeria Cordero (Comercial)", "demo.admincomercial@aerotrack.test", "admin_comercial"),
    ("Diego Manosalvas (Operaciones)", "demo.adminoperaciones@aerotrack.test", "admin_operaciones"),
    ("Camila Rosero (Ventas)", "demo.adminventas@aerotrack.test", "admin_ventas"),
    ("Mateo Villacís (Clientes)", "demo.adminclientes@aerotrack.test", "admin_clientes"),
    ("Fernanda Cevallos (Agente)", "demo.agente@aerotrack.test", "Agente"),
]


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


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


def main() -> None:
    headers = {"Authorization": admin_token()}

    print(f"{'Rol':<18} {'Email':<38} {'Contraseña'}")
    print("-" * 75)
    for nombre_completo, email, rol_nombre in USUARIOS_DEMO:
        rol = get_first(headers, "roles", f'nombre="{rol_nombre}"')
        if rol is None:
            print(f"! rol '{rol_nombre}' no encontrado — correr scripts/seed_roles_departamento.py primero")
            continue

        existente = get_first(headers, "usuarios", f'email="{email}"')
        if existente is None:
            resp = httpx.post(
                f"{PB_URL}/api/collections/usuarios/records",
                json={
                    "email": email,
                    "password": PASSWORD_DEMO,
                    "passwordConfirm": PASSWORD_DEMO,
                    "nombre_completo": nombre_completo,
                    "rol_id": rol["id"],
                    "activo": True,
                    "emailVisibility": True,
                },
                headers=headers,
                timeout=10,
            )
            if resp.status_code >= 400:
                print(f"! error creando {email}: {resp.text}")
                continue
        else:
            # Rota la contraseña al valor conocido (verificado en vivo: un
            # PATCH de `password` invalida cualquier sesión previa, ver
            # `usuarios_service.cerrar_sesiones_activas`) — así el script es
            # seguro de re-correr sin perder el acceso a la cuenta demo.
            resp = httpx.patch(
                f"{PB_URL}/api/collections/usuarios/records/{existente['id']}",
                json={"password": PASSWORD_DEMO, "passwordConfirm": PASSWORD_DEMO, "rol_id": rol["id"]},
                headers=headers,
                timeout=10,
            )
            if resp.status_code >= 400:
                print(f"! error actualizando {email}: {resp.text}")
                continue

        print(f"{rol_nombre:<18} {email:<38} {PASSWORD_DEMO}")


if __name__ == "__main__":
    main()
