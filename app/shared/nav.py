"""Navegación del backoffice — catálogo de los 6 módulos operativos,
agrupados en el sidebar y filtrados por el RBAC Nivel 1 (permiso "ver")
del usuario autenticado. Cada módulo agrega sus propias `items` aquí
cuando construya pantallas de backoffice; mientras no las tenga, aparece
como grupo deshabilitado con badge "Próximamente" (si el usuario tiene
acceso Nivel 1 al módulo, aunque la pantalla todavía no exista).
"""

from app.shared.pocketbase_client import get_pocketbase_client

MODULOS_CATALOGO = [
    {
        "clave": "seguridad",
        "nombre": "Seguridad",
        "icono": "bi-shield-lock",
        "items": [
            {"label": "Usuarios", "href": "/admin/usuarios", "icono": "bi-people"},
            {"label": "Roles", "href": "/admin/roles", "icono": "bi-diagram-3"},
            {"label": "Auditoría", "href": "/admin/auditoria", "icono": "bi-journal-text"},
        ],
    },
    {"clave": "pasajeros", "nombre": "Pasajeros", "icono": "bi-person-badge", "items": []},
    {
        "clave": "vuelos_catalogo",
        "nombre": "Vuelos",
        "icono": "bi-airplane",
        "items": [
            {"label": "Forzar estado (demo)", "href": "/backoffice/vuelos/forzar-estado", "icono": "bi-exclamation-diamond"},
        ],
    },
    {
        "clave": "reservas",
        "nombre": "Reservas",
        "icono": "bi-calendar-check",
        "items": [
            {"label": "Reserva asistida", "href": "/backoffice/reservas/nueva", "icono": "bi-headset"},
        ],
    },
    {"clave": "disrupciones", "nombre": "Disrupciones", "icono": "bi-exclamation-triangle", "items": []},
    {
        "clave": "facturacion",
        "nombre": "Facturación",
        "icono": "bi-receipt",
        "items": [
            {"label": "Comisiones", "href": "/backoffice/comisiones", "icono": "bi-percent"},
            {"label": "Remesas", "href": "/backoffice/remesas", "icono": "bi-bank"},
        ],
    },
]


async def modulos_con_acceso(usuario: dict) -> list[dict]:
    """Módulos del catálogo sobre los que el rol del usuario tiene permiso
    Nivel 1 "ver". Pasajeros (sin `rol_id`) no ven ningún grupo — su acceso
    es de autoservicio, no de backoffice."""
    rol_id = usuario.get("rol_id")
    if not rol_id:
        return []

    client = get_pocketbase_client()
    modulos = (await client.list_records("modulos", {"perPage": 200}))["items"]
    modulo_id_por_clave = {m["clave"]: m["id"] for m in modulos}

    permisos_ver = (await client.list_records(
        "permisos", {"filter": 'accion="ver"', "perPage": 200}
    ))["items"]
    permiso_ver_id_por_modulo_id = {p["modulo_id"]: p["id"] for p in permisos_ver}

    roles_permisos = (await client.list_records(
        "roles_permisos", {"filter": f'rol_id="{rol_id}"', "perPage": 500}
    ))["items"]
    permisos_del_rol = {rp["permiso_id"] for rp in roles_permisos}

    return [
        entry
        for entry in MODULOS_CATALOGO
        if (modulo_id := modulo_id_por_clave.get(entry["clave"]))
        and (permiso_id := permiso_ver_id_por_modulo_id.get(modulo_id))
        and permiso_id in permisos_del_rol
    ]


async def nav_context(usuario: dict) -> dict:
    return {"usuario": usuario, "nav_modulos": await modulos_con_acceso(usuario)}
