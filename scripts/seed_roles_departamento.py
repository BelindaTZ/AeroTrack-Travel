"""Siembra idempotente del punto 7 de `docs/aerotrack-travel-cambios-pendientes.md`
— Roles RBAC por departamento (CU-O09/CU-O112).

Crea 6 roles nuevos (el 7mo de la tabla, "agente", ya existe como el rol de
sistema "Agente" sembrado por `seed_seguridad.py` — no se duplica) y les
otorga permisos Nivel 1 sobre los módulos que les corresponden por
departamento. También agrega el módulo "paquetes" (no existía — hace falta
para el CRUD de % de descuento, CU-T14) y la acción "editar" a
"disrupciones" (hace falta para configurar umbrales de riesgo, CU-T20).

Requiere que TODOS los demás scripts de seed ya hayan corrido — lee los
módulos/acciones que esos scripts ya registraron (`seguridad`,
`integraciones`, `centro_ayuda`, `ofertas`, `asistente_ia`, `autos`,
`carrito`, más los core de `seed_seguridad.py`) en vez de asumir una lista
fija, para no desincronizarse si esos scripts cambian.

NOTA 2026-07-27: este script originalmente también creaba `admin_general`
("acceso total", con TODOS los permisos otorgados uno por uno) como
duplicado funcional del rol de sistema "Administrador" — el usuario lo
vio como una confusión real ("dos roles de admin") y pidió eliminarlo.
Se quitó del catálogo; "Administrador" sigue siendo el único rol de
acceso total. No reintroducir sin que el usuario lo pida explícitamente.

Ejecutar: python scripts/seed_roles_departamento.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

# (nombre, descripcion) — es_sistema=False (a diferencia de los 3 roles
# base): ningún código de negocio depende de estos nombres, el admin los
# puede editar/borrar libremente desde /admin/roles.
ROLES_DEPARTAMENTO = [
    ("admin_ti", "Seguridad, Integraciones y Configuración del sistema"),
    ("admin_finanzas", "Facturación y reportes financieros"),
    ("admin_comercial", "Ofertas, Asistente IA y reportes de marketing"),
    ("admin_operaciones", "Disrupciones, Centro de Ayuda y monitoreo de vuelos activos"),
    ("admin_ventas", "Módulos de producto (vuelos, autos, paquetes) y reportes de ventas"),
    ("admin_clientes", "Pasajeros y reportes de captación/segmentación de clientes"),
]

# rol -> {modulo_clave: [acciones]} — Nivel 1.
MATRIZ = {
    "admin_ti": {
        "seguridad": ["ver", "crear", "editar", "eliminar"],
        "integraciones": ["ver", "editar", "ejecutar"],
        "configuracion": ["ver", "editar"],
        "vuelos_catalogo": ["ver"],
    },
    "admin_finanzas": {
        "facturacion": ["ver", "crear", "editar", "exportar", "eliminar"],
        # agregado 2026-08-01 (WP-18, auditoría de WorkPanels) — métodos de
        # pago (procesadores Stripe) son tan de Finanzas como de TI; sin
        # esto, admin_finanzas no podía entrar a ninguna pantalla de
        # /admin/configuracion, aunque el propio doc de la auditoría ya
        # nombraba a admin_finanzas como rol con acceso a este WP.
        "configuracion": ["ver", "editar"],
    },
    "admin_comercial": {
        "ofertas": ["ver", "crear", "editar"],
        "asistente_ia": ["ver", "editar"],
    },
    "admin_operaciones": {
        "disrupciones": ["ver", "ejecutar", "editar"],
        "centro_ayuda": ["ver", "crear", "editar"],
        "vuelos_catalogo": ["ver"],
    },
    "admin_ventas": {
        "vuelos_catalogo": ["ver", "crear", "editar"],
        # "eliminar" agregado 2026-07-31 (WP-04, auditoría de WorkPanels) —
        # no habilita ningún borrado literal (no existe endpoint para eso),
        # es el flag que ya usan cancelar_reserva_service/router_reservas/
        # router_documentos para "acceso a cualquier reserva, no solo las
        # propias" (mismo patrón que ya usa admin_clientes en pasajeros más
        # abajo). Sin esto, admin_ventas no podía ver detalle/cancelar/
        # descargar voucher de una reserva que no gestionó personalmente.
        "reservas": ["ver", "crear", "editar", "eliminar"],
        "autos": ["ver", "crear", "editar"],
        "paquetes": ["ver", "editar"],
    },
    "admin_clientes": {
        "pasajeros": ["ver", "crear", "editar", "eliminar"],
    },
}

# Módulo nuevo (CU-T14 — % de descuento por tipo de paquete, sin pantalla
# de gestión hasta ahora).
MODULO_PAQUETES = ("paquetes", "Paquetes", "Combinaciones de descuento y armado de paquetes", 90)


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

    # ── módulo "paquetes" (CU-T14) ──────────────────────────────────────
    clave, nombre, descripcion, orden = MODULO_PAQUETES
    modulo_paquetes = get_first(headers, "modulos", f'clave="{clave}"')
    if modulo_paquetes is None:
        modulo_paquetes = create(
            headers, "modulos",
            {"clave": clave, "nombre_display": nombre, "descripcion": descripcion, "orden": orden},
        )
        print(f"+ modulo {clave}")
    else:
        print(f"= modulo {clave} ya existe")

    ya_tiene_tabla = any(
        mt["modulo_id"] == modulo_paquetes["id"] and mt["tabla"] == "tipos_paquete_descuento"
        for mt in get_all(headers, "modulo_tablas")
    )
    if ya_tiene_tabla:
        print("= modulo_tablas paquetes.tipos_paquete_descuento ya existe")
    else:
        create(
            headers, "modulo_tablas",
            {"modulo_id": modulo_paquetes["id"], "tabla": "tipos_paquete_descuento",
             "descripcion": "Tabla 'tipos_paquete_descuento' del módulo paquetes"},
        )
        print("+ modulo_tablas paquetes.tipos_paquete_descuento")

    permisos_paquetes_existentes = {
        p["accion"] for p in get_all(headers, "permisos") if p["modulo_id"] == modulo_paquetes["id"]
    }
    for accion in ("ver", "editar"):
        if accion in permisos_paquetes_existentes:
            print(f"= permiso paquetes.{accion} ya existe")
            continue
        create(headers, "permisos", {"modulo_id": modulo_paquetes["id"], "accion": accion})
        print(f"+ permiso paquetes.{accion}")

    # ── acción "editar" en disrupciones (CU-T20) ────────────────────────
    modulo_disrupciones = get_first(headers, "modulos", 'clave="disrupciones"')
    if modulo_disrupciones is None:
        raise RuntimeError("Módulo 'disrupciones' no sembrado — correr scripts/seed_seguridad.py primero")
    permiso_editar_disrupciones = get_first(
        headers, "permisos", f'modulo_id="{modulo_disrupciones["id"]}" && accion="editar"'
    )
    if permiso_editar_disrupciones is None:
        permiso_editar_disrupciones = create(
            headers, "permisos", {"modulo_id": modulo_disrupciones["id"], "accion": "editar"}
        )
        print("+ permiso disrupciones.editar")
        # Administrador ya tiene acceso total por diseño de este módulo —
        # se lo otorgamos explícito acá porque esta acción es nueva y
        # seed_seguridad.py no la conocía cuando corrió.
        rol_admin = get_first(headers, "roles", 'nombre="Administrador"')
        if rol_admin:
            create(headers, "roles_permisos", {"rol_id": rol_admin["id"], "permiso_id": permiso_editar_disrupciones["id"]})
            print("+ roles_permisos Administrador -> disrupciones.editar")
    else:
        print("= permiso disrupciones.editar ya existe")

    # ── configuracion_sistema.simulador_disrupciones.umbral_riesgo_pct
    # (CU-T20) — riesgo_service.py ya la lee con fallback a 20.0 si no
    # está sembrada; acá se siembra el valor inicial editable desde la
    # nueva pantalla /backoffice/disrupciones/config-riesgo.
    config_existente = {c["clave"] for c in get_all(headers, "configuracion_sistema")}
    clave_umbral = "simulador_disrupciones.umbral_riesgo_pct"
    if clave_umbral in config_existente:
        print(f"= configuracion_sistema {clave_umbral} ya existe")
    else:
        rol_admin_cfg = get_first(headers, "roles", 'nombre="Administrador"')
        admins = get_all(headers, "usuarios") if rol_admin_cfg is None else [
            u for u in get_all(headers, "usuarios") if u.get("rol_id") == rol_admin_cfg["id"]
        ]
        if admins:
            create(
                headers, "configuracion_sistema",
                {
                    "clave": clave_umbral, "valor": "20", "categoria": "simulador_disrupciones",
                    "descripcion": "% de riesgo estimado a partir del cual se dispara alerta proactiva (CU-T20)",
                    "modificado_por": admins[0]["id"],
                },
            )
            print(f"+ configuracion_sistema {clave_umbral}")

    # ── roles de departamento (upsert por nombre) ───────────────────────
    roles_existentes = {r["nombre"]: r for r in get_all(headers, "roles")}
    for nombre, descripcion in ROLES_DEPARTAMENTO:
        if nombre in roles_existentes:
            print(f"= rol {nombre} ya existe")
            continue
        roles_existentes[nombre] = create(
            headers, "roles",
            {"nombre": nombre, "descripcion": descripcion, "es_sistema": False, "tipo_panel": "backoffice"},
        )
        print(f"+ rol {nombre}")

    modulos_por_clave = {m["clave"]: m for m in get_all(headers, "modulos")}
    permisos_todos = get_all(headers, "permisos")
    permisos_por_clave = {(p["modulo_id"], p["accion"]): p for p in permisos_todos}
    roles_permisos_existentes = {(rp["rol_id"], rp["permiso_id"]) for rp in get_all(headers, "roles_permisos")}

    def otorgar(rol_id: str, permiso_id: str, etiqueta: str) -> None:
        key = (rol_id, permiso_id)
        if key in roles_permisos_existentes:
            return
        create(headers, "roles_permisos", {"rol_id": rol_id, "permiso_id": permiso_id})
        roles_permisos_existentes.add(key)
        print(f"+ roles_permisos {etiqueta}")

    # ── según MATRIZ ──────────────────────────────────────────────────
    for rol_nombre, permisos_modulo in MATRIZ.items():
        rol_id = roles_existentes[rol_nombre]["id"]
        for modulo_clave, acciones in permisos_modulo.items():
            modulo = modulos_por_clave.get(modulo_clave)
            if modulo is None:
                print(f"  ! módulo '{modulo_clave}' no encontrado — saltando {rol_nombre}.{modulo_clave}")
                continue
            for accion in acciones:
                permiso = permisos_por_clave.get((modulo["id"], accion))
                if permiso is None:
                    print(f"  ! permiso {modulo_clave}.{accion} no encontrado — saltando")
                    continue
                otorgar(rol_id, permiso["id"], f"{rol_nombre} -> {modulo_clave}.{accion}")

    print("Listo.")


if __name__ == "__main__":
    main()
