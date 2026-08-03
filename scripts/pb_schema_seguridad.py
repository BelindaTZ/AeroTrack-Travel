"""Crea (idempotente) las 9 colecciones propias del módulo Seguridad en
pocketbase-travel. Requiere PB_TRAVEL_URL/PB_TRAVEL_EMAIL/PB_TRAVEL_PASSWORD
en el entorno (.env) — sin credenciales hardcodeadas (REG-B3).

Todas las colecciones quedan con listRule/viewRule/createRule/updateRule/
deleteRule = null (solo admin de PocketBase): el backend FastAPI es el único
cliente autorizado a hablar con pocketbase-travel, siempre con el token de
admin; el RBAC de dos niveles y la autenticación de usuario final se
resuelven en la capa de aplicación (rbac_service / session_service), no en
las reglas de PocketBase.

Ejecutar: python scripts/pb_schema_seguridad.py
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def existing_collections(headers: dict) -> dict[str, dict]:
    resp = httpx.get(f"{PB_URL}/api/collections", params={"perPage": 200}, headers=headers, timeout=10)
    resp.raise_for_status()
    return {c["name"]: c for c in resp.json()["items"]}


def get_all_records(headers: dict, collection: str) -> list[dict]:
    resp = httpx.get(
        f"{PB_URL}/api/collections/{collection}/records",
        params={"perPage": 200},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["items"]


def ensure_collection(headers: dict, payload: dict, cache: dict[str, dict]) -> dict:
    name = payload["name"]
    if name in cache:
        print(f"  = {name} ya existe, se omite")
        return cache[name]
    resp = httpx.post(f"{PB_URL}/api/collections", json=payload, headers=headers, timeout=10)
    if resp.status_code >= 400:
        print(f"  ! error creando {name}: {resp.status_code} {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    created = resp.json()
    cache[name] = created
    print(f"  + {name} creada (id={created['id']})")
    return created


def text_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "text", "required": required, "options": {}}


def bool_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "bool", "required": required, "options": {}}


def select_field(name: str, values: list[str], required: bool = False) -> dict:
    return {
        "name": name,
        "type": "select",
        "required": required,
        "options": {"maxSelect": 1, "values": values},
    }


def relation_field(name: str, target_collection_id: str, required: bool = False) -> dict:
    return {
        "name": name,
        "type": "relation",
        "required": required,
        "options": {"collectionId": target_collection_id, "cascadeDelete": False, "maxSelect": 1},
    }


def json_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "json", "required": required, "options": {}}


def number_field(name: str, required: bool = False) -> dict:
    return {"name": name, "type": "number", "required": required, "options": {}}


def remove_field(headers: dict, collection: dict, field_name: str) -> None:
    """Quita un campo ya existente de una colección (PATCH del schema sin
    esa entrada). Usado para dar de baja `usuarios.tipo_actor` — correr
    DESPUÉS de que el código deje de escribirlo y de que `roles.tipo_panel`
    ya esté sembrado, para no perder capacidad de resolver el panel de una
    cuenta en el medio de la migración."""
    if not any(f["name"] == field_name for f in collection["schema"]):
        print(f"  = {collection['name']}.{field_name}: ya no existe, se omite")
        return
    schema_actualizado = [f for f in collection["schema"] if f["name"] != field_name]
    resp = httpx.patch(
        f"{PB_URL}/api/collections/{collection['id']}",
        json={"schema": schema_actualizado},
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        print(f"  ! error quitando {collection['name']}.{field_name}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    print(f"  - {collection['name']}.{field_name} eliminado")


LOCKED_RULES = {
    "listRule": None,
    "viewRule": None,
    "createRule": None,
    "updateRule": None,
    "deleteRule": None,
}


def main() -> None:
    headers = {"Authorization": admin_token()}
    cache = existing_collections(headers)
    print("Verificando/creando colecciones de Seguridad...")

    modulos = ensure_collection(
        headers,
        {
            "name": "modulos",
            "type": "base",
            "schema": [
                text_field("clave", required=True),
                text_field("nombre_display", required=True),
                text_field("descripcion"),
                number_field("orden"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    roles = ensure_collection(
        headers,
        {
            "name": "roles",
            "type": "base",
            "schema": [
                text_field("nombre", required=True),
                text_field("descripcion"),
                bool_field("es_sistema"),
                # MODIFICADA 2026-07-27 — reemplaza a `usuarios.tipo_actor`.
                # A qué panel corresponde una cuenta es una propiedad del ROL
                # (siempre coherente con sus permisos de módulo), no algo que
                # cada usuario deba fijar aparte y que pueda desalinearse.
                select_field("tipo_panel", ["backoffice", "autoservicio"], required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    permisos = ensure_collection(
        headers,
        {
            "name": "permisos",
            "type": "base",
            "schema": [
                relation_field("modulo_id", modulos["id"], required=True),
                select_field(
                    "accion",
                    ["ver", "crear", "editar", "eliminar", "exportar", "ejecutar"],
                    required=True,
                ),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "roles_permisos",
            "type": "base",
            "schema": [
                relation_field("rol_id", roles["id"], required=True),
                relation_field("permiso_id", permisos["id"], required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "roles_permisos_tablas",
            "type": "base",
            "schema": [
                relation_field("rol_id", roles["id"], required=True),
                relation_field("modulo_id", modulos["id"], required=True),
                text_field("tabla", required=True),
                # Agregado 2026-07-30 (ver pb_schema_seguridad_fix_nivel2_accion.py
                # para instalaciones que ya tenían esta colección creada) — Nivel 2
                # restringe por (tabla, accion), no solo por tabla. Solo el
                # subconjunto de acciones con sentido sobre registros de una tabla
                # puntual; "ejecutar"/"exportar" quedan exclusivas de Nivel 1.
                select_field("accion", ["ver", "crear", "editar", "eliminar"], required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "modulo_tablas",
            "type": "base",
            "schema": [
                relation_field("modulo_id", modulos["id"], required=True),
                text_field("tabla", required=True),
                text_field("descripcion"),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    usuarios = ensure_collection(
        headers,
        {
            "name": "usuarios",
            "type": "auth",
            # `tipo_actor` (2026-07-27) se retiró de acá — ver `roles.tipo_panel`
            # arriba: qué panel corresponde a esta cuenta se deriva siempre de
            # `rol_id`, nunca de un campo propio que pudiera desalinearse.
            "schema": [
                text_field("nombre_completo", required=True),
                relation_field("rol_id", roles["id"], required=True),
                bool_field("activo"),
            ],
            "options": {
                "allowEmailAuth": True,
                "allowOAuth2Auth": False,
                "allowUsernameAuth": False,
                "requireEmail": True,
                "minPasswordLength": 8,
            },
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "auditoria",
            "type": "base",
            "schema": [
                relation_field("usuario_id", usuarios["id"], required=False),
                text_field("accion", required=True),
                text_field("tabla", required=True),
                text_field("registro_id"),
                json_field("detalle"),
                text_field("ip"),
            ],
            # NOTA: PocketBase no permite bloquear a un admin autenticado vía
            # reglas de colección (los tokens de admin bypasean listRule/
            # updateRule/etc. siempre, no hay sintaxis de regla que se aplique
            # a ellos). Como el backend habla con PocketBase únicamente con
            # token de admin, RN-SEG-010/REG-B4 (solo inserción) se garantiza
            # exclusivamente en la capa de aplicación: `audit_service` nunca
            # expone update()/delete() y ningún router los invoca.
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_collection(
        headers,
        {
            "name": "configuracion_sistema",
            "type": "base",
            "schema": [
                text_field("clave", required=True),
                text_field("valor", required=True),
                text_field("categoria", required=True),
                text_field("descripcion"),
                text_field("modificado_por", required=True),
            ],
            **LOCKED_RULES,
        },
        cache,
    )

    ensure_fields(
        headers,
        usuarios,
        [
            # RF-SEG-004/005 — token de recuperación de contraseña de un solo
            # uso: se guarda un hash SHA-256, no el token en claro (RNF-SEG-001
            # aplica el mismo espíritu a este secreto temporal).
            text_field("reset_token_hash"),
            {"name": "reset_token_expira", "type": "date", "required": False, "options": {}},
        ],
    )

    # MIGRACIÓN 2026-07-27 — `rol_id` pasa a obligatorio para los 3 tipos de
    # actor (antes pasajero quedaba sin rol). Correr scripts/seed_seguridad.py
    # primero: siembra el rol "Pasajero" y hace el backfill de los usuarios
    # pasajero existentes, así ninguno queda con `rol_id` vacío al aplicar
    # este `required=True`.
    set_field_required(headers, usuarios, "rol_id", required=True)

    # MIGRACIÓN 2026-07-27 (2/2) — `roles.tipo_panel` reemplaza a
    # `usuarios.tipo_actor`. Se agrega acá como no-obligatorio (por si esta
    # corrida es la primera vez que existe la columna); correr
    # scripts/seed_seguridad.py para sembrar el valor de los 3 roles de
    # sistema, y recién DESPUÉS correr este script una segunda vez para que
    # las dos líneas de abajo se apliquen: recién ahí es seguro exigir
    # `tipo_panel` y borrar la columna vieja sin perder la capacidad de
    # resolver a qué panel corresponde cada cuenta.
    ensure_fields(
        headers, roles, [select_field("tipo_panel", ["backoffice", "autoservicio"], required=False)]
    )
    if all(r.get("tipo_panel") for r in get_all_records(headers, "roles")):
        set_field_required(headers, roles, "tipo_panel", required=True)
        remove_field(headers, usuarios, "tipo_actor")
    else:
        print("  ! hay roles sin tipo_panel todavía — corré seed_seguridad.py y volvé a correr este script")

    print("Listo.")


def set_field_required(headers: dict, collection: dict, field_name: str, required: bool = True) -> None:
    """Actualiza el flag `required` de un campo ya existente en la colección
    (a diferencia de `ensure_fields`, que solo agrega campos nuevos). Usado
    para migrar `usuarios.rol_id` a obligatorio — correr el backfill de
    `scripts/seed_seguridad.py` ANTES de esto, para que ningún usuario
    existente quede con `rol_id` vacío cuando el campo pase a requerido."""
    campo = next((f for f in collection["schema"] if f["name"] == field_name), None)
    if campo is None:
        raise ValueError(f"{collection['name']}: campo {field_name!r} no existe")
    if campo.get("required") == required:
        print(f"  = {collection['name']}.{field_name}: required ya es {required}")
        return
    schema_actualizado = [
        {**f, "required": required} if f["name"] == field_name else f for f in collection["schema"]
    ]
    resp = httpx.patch(
        f"{PB_URL}/api/collections/{collection['id']}",
        json={"schema": schema_actualizado},
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        print(f"  ! error actualizando {collection['name']}.{field_name}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    print(f"  + {collection['name']}.{field_name}: required={required}")


def ensure_fields(headers: dict, collection: dict, nuevos_campos: list[dict]) -> None:
    existentes = {f["name"] for f in collection["schema"]}
    faltantes = [f for f in nuevos_campos if f["name"] not in existentes]
    if not faltantes:
        print(f"  = {collection['name']}: campos ya presentes, se omite")
        return
    schema_actualizado = collection["schema"] + faltantes
    resp = httpx.patch(
        f"{PB_URL}/api/collections/{collection['id']}",
        json={"schema": schema_actualizado},
        headers=headers,
        timeout=10,
    )
    if resp.status_code >= 400:
        print(f"  ! error agregando campos a {collection['name']}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    print(f"  + {collection['name']}: agregados {[f['name'] for f in faltantes]}")


if __name__ == "__main__":
    main()

