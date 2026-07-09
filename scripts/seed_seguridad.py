"""Siembra idempotente del catálogo base de Seguridad: módulos, roles de
sistema, permisos (Nivel 1) y su asignación a los 3 roles base, más el
catálogo `modulo_tablas`. Nunca sobreescribe un registro ya existente
(upsert por clave natural, no por id) — seguro de re-ejecutar.

Requiere que la colección `usuarios` ya tenga al menos un administrador
(el bootstrap de PocketBase / registro manual del primer admin es un paso
fuera de alcance de este script).

Ejecutar: python scripts/seed_seguridad.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

MODULOS = [
    ("seguridad", "Seguridad", "Usuarios, roles, permisos y auditoría", 10),
    ("configuracion", "Configuración", "Panel general y parámetros del sistema", 20),
    ("pasajeros", "Pasajeros", "Registro, historial y gestión backoffice", 30),
    ("vuelos_catalogo", "Vuelos (catálogo)", "Búsqueda, tarifas y estado de vuelos programables", 40),
    ("reservas", "Reservas", "Autoservicio, asistida, modificación y cancelación", 50),
    ("disrupciones", "Disrupciones y Notificaciones", "Detección y aviso de cambios operacionales", 60),
    ("facturacion", "Facturación", "Pagos, comisiones, remesas, reembolsos y facturas", 70),
]

ROLES = [
    ("Administrador", "Acceso total al backoffice", True),
    ("Agente", "Reservas asistidas y soporte a pasajeros", True),
    ("Pasajero", "Autoservicio de reserva y gestión propia", True),
]

# (clave_modulo, [acciones]) — Nivel 1 disponible por módulo
PERMISOS_POR_MODULO = {
    "seguridad": ["ver", "crear", "editar", "eliminar"],
    "configuracion": ["ver", "editar"],
    "pasajeros": ["ver", "crear", "editar", "eliminar"],
    "vuelos_catalogo": ["ver", "crear", "editar"],
    "reservas": ["ver", "crear", "editar", "eliminar"],
    "disrupciones": ["ver", "ejecutar"],
    "facturacion": ["ver", "crear", "editar", "exportar"],
}

# rol -> {modulo_clave: [acciones autorizadas]}
MATRIZ_ROLES_PERMISOS = {
    "Administrador": PERMISOS_POR_MODULO,  # acceso total
    "Agente": {
        "pasajeros": ["ver", "crear", "editar"],
        "vuelos_catalogo": ["ver", "crear", "editar"],
        "reservas": ["ver", "crear", "editar"],
        "disrupciones": ["ver"],
        "facturacion": ["ver", "crear", "editar"],
    },
    "Pasajero": {
        "reservas": ["ver"],
        "disrupciones": ["ver"],
        "facturacion": ["ver"],
    },
}

MODULO_TABLAS = {
    "seguridad": ["usuarios", "roles", "permisos", "roles_permisos", "roles_permisos_tablas", "auditoria"],
    "configuracion": ["configuracion_sistema", "metodos_pago", "politicas_reembolso", "niveles_tarifa"],
    "pasajeros": ["pasajeros"],
    "vuelos_catalogo": ["vuelos_catalogo", "tarifas_vuelo", "aerolineas"],
    "reservas": ["reservas", "reserva_pasajeros", "reserva_extras", "alertas_precio"],
    "disrupciones": ["disrupciones", "notificaciones"],
    "facturacion": ["pagos", "comisiones", "remesas", "remesa_comisiones", "reembolsos", "facturas"],
}


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
        f"{PB_URL}/api/collections/{collection}/records",
        params={"perPage": 200},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["items"]


def create(headers: dict, collection: str, data: dict) -> dict:
    resp = httpx.post(
        f"{PB_URL}/api/collections/{collection}/records", json=data, headers=headers, timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    headers = {"Authorization": admin_token()}

    # ── módulos (upsert por `clave`) ────────────────────────────────────
    existentes = {m["clave"]: m for m in get_all(headers, "modulos")}
    for clave, nombre, descripcion, orden in MODULOS:
        if clave in existentes:
            continue
        existentes[clave] = create(
            headers,
            "modulos",
            {"clave": clave, "nombre_display": nombre, "descripcion": descripcion, "orden": orden},
        )
        print(f"+ modulo {clave}")
    modulos_por_clave = existentes

    # ── roles (upsert por `nombre`) ─────────────────────────────────────
    roles_existentes = {r["nombre"]: r for r in get_all(headers, "roles")}
    for nombre, descripcion, es_sistema in ROLES:
        if nombre in roles_existentes:
            continue
        roles_existentes[nombre] = create(
            headers, "roles", {"nombre": nombre, "descripcion": descripcion, "es_sistema": es_sistema}
        )
        print(f"+ rol {nombre}")

    # ── permisos (upsert por (modulo_id, accion)) ───────────────────────
    permisos_existentes = get_all(headers, "permisos")
    permisos_por_clave = {(p["modulo_id"], p["accion"]): p for p in permisos_existentes}
    for modulo_clave, acciones in PERMISOS_POR_MODULO.items():
        modulo_id = modulos_por_clave[modulo_clave]["id"]
        for accion in acciones:
            key = (modulo_id, accion)
            if key in permisos_por_clave:
                continue
            permisos_por_clave[key] = create(
                headers, "permisos", {"modulo_id": modulo_id, "accion": accion}
            )
            print(f"+ permiso {modulo_clave}.{accion}")

    # ── roles_permisos (Nivel 1, upsert por (rol_id, permiso_id)) ───────
    roles_permisos_existentes = get_all(headers, "roles_permisos")
    rp_keys = {(rp["rol_id"], rp["permiso_id"]) for rp in roles_permisos_existentes}
    for rol_nombre, permisos_modulo in MATRIZ_ROLES_PERMISOS.items():
        rol_id = roles_existentes[rol_nombre]["id"]
        for modulo_clave, acciones in permisos_modulo.items():
            modulo_id = modulos_por_clave[modulo_clave]["id"]
            for accion in acciones:
                permiso = permisos_por_clave[(modulo_id, accion)]
                key = (rol_id, permiso["id"])
                if key in rp_keys:
                    continue
                create(headers, "roles_permisos", {"rol_id": rol_id, "permiso_id": permiso["id"]})
                rp_keys.add(key)
                print(f"+ roles_permisos {rol_nombre} -> {modulo_clave}.{accion}")

    # ── modulo_tablas (upsert por (modulo_id, tabla)) ───────────────────
    modulo_tablas_existentes = get_all(headers, "modulo_tablas")
    mt_keys = {(mt["modulo_id"], mt["tabla"]) for mt in modulo_tablas_existentes}
    for modulo_clave, tablas in MODULO_TABLAS.items():
        modulo_id = modulos_por_clave[modulo_clave]["id"]
        for tabla in tablas:
            key = (modulo_id, tabla)
            if key in mt_keys:
                continue
            create(
                headers,
                "modulo_tablas",
                {
                    "modulo_id": modulo_id,
                    "tabla": tabla,
                    "descripcion": f"Tabla '{tabla}' del módulo {modulo_clave}",
                },
            )
            mt_keys.add(key)
            print(f"+ modulo_tablas {modulo_clave}.{tabla}")

    # ── configuracion_sistema: expiración del enlace de recuperación ───
    # (RNF-SEG-004) — política de fortaleza de contraseña se deja como
    # default documentado en password_service.py (RNF-SEG-007 lo permite
    # explícitamente si la clave no existe en configuracion_sistema).
    config_existente = {c["clave"] for c in get_all(headers, "configuracion_sistema")}
    if "password_reset.expiracion_minutos" not in config_existente:
        admins = httpx.get(
            f"{PB_URL}/api/collections/usuarios/records",
            headers=headers,
            params={"filter": 'tipo_actor="administrador"', "perPage": 1},
            timeout=10,
        ).json()["items"]
        if admins:
            create(
                headers,
                "configuracion_sistema",
                {
                    "clave": "password_reset.expiracion_minutos",
                    "valor": "30",
                    "categoria": "expiraciones",
                    "descripcion": "Minutos de validez del enlace de recuperación de contraseña (RNF-SEG-004)",
                    "modificado_por": admins[0]["id"],
                },
            )
            print("+ configuracion_sistema password_reset.expiracion_minutos")

    print("Listo.")


if __name__ == "__main__":
    main()
