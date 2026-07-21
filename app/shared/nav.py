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
    {
        "clave": "pasajeros",
        "nombre": "Pasajeros",
        "icono": "bi-person-badge",
        "items": [
            {"label": "Buscar pasajeros", "href": "/backoffice/pasajeros", "icono": "bi-search"},
        ],
    },
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
    {
        "clave": "disrupciones",
        "nombre": "Disrupciones",
        "icono": "bi-exclamation-triangle",
        "items": [
            {"label": "Notificaciones", "href": "/backoffice/notificaciones", "icono": "bi-bell"},
        ],
    },
    {
        "clave": "facturacion",
        "nombre": "Facturación",
        "icono": "bi-receipt",
        "items": [
            {"label": "Comisiones", "href": "/backoffice/comisiones", "icono": "bi-percent"},
            {"label": "Remesas", "href": "/backoffice/remesas", "icono": "bi-bank"},
        ],
    },
    {
        "clave": "integraciones",
        "nombre": "Integraciones",
        "icono": "bi-plug",
        "items": [
            {"label": "Fuentes de datos", "href": "/backoffice/integraciones/fuentes", "icono": "bi-plug"},
            {"label": "Bitácora de sincronizaciones", "href": "/backoffice/integraciones/bitacora", "icono": "bi-journal-text"},
        ],
    },
    {
        "clave": "centro_ayuda",
        "nombre": "Centro de Ayuda",
        "icono": "bi-question-circle",
        "items": [
            {"label": "Artículos", "href": "/backoffice/ayuda/articulos", "icono": "bi-journal-text"},
            {"label": "Métricas", "href": "/backoffice/ayuda/metricas", "icono": "bi-graph-up"},
            {"label": "Casos escalados", "href": "/backoffice/ayuda/casos", "icono": "bi-headset"},
        ],
    },
    {
        "clave": "ofertas",
        "nombre": "Ofertas y Marketing",
        "icono": "bi-stars",
        "items": [
            {"label": "Cupones", "href": "/backoffice/ofertas/cupones", "icono": "bi-ticket-perforated"},
            {"label": "Reporte de cupones", "href": "/backoffice/ofertas/reporte-cupones", "icono": "bi-graph-up"},
            {"label": "Campañas de email", "href": "/backoffice/ofertas/campanas", "icono": "bi-envelope-paper"},
            {"label": "Acumulación con paquete", "href": "/backoffice/ofertas/config-acumulacion-paquete", "icono": "bi-sliders"},
        ],
    },
    {
        "clave": "asistente_ia",
        "nombre": "Asistente IA",
        "icono": "bi-robot",
        "items": [
            {"label": "Configuración", "href": "/backoffice/asistente/configuracion", "icono": "bi-sliders"},
            {"label": "Reporte de consultas", "href": "/backoffice/asistente/reporte", "icono": "bi-graph-up"},
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
