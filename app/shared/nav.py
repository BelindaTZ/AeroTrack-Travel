"""Navegación del backoffice — catálogo de los 6 módulos operativos,
agrupados en el sidebar y filtrados por el RBAC Nivel 1 (permiso "ver")
del usuario autenticado. Cada módulo agrega sus propias `items` aquí
cuando construya pantallas de backoffice; mientras no las tenga, aparece
como grupo deshabilitado con badge "Próximamente" (si el usuario tiene
acceso Nivel 1 al módulo, aunque la pantalla todavía no exista).
"""

from app.seguridad.services.rbac_service import tiene_permiso
from app.shared.pocketbase_client import get_pocketbase_client

# Cada dashboard es una "tabla" (Nivel 2 de rbac_service) dentro del único
# módulo "dashboards" — ver scripts/seed_dashboards_rbac.py sobre por qué
# (permisos.accion no admite acciones custom tipo "ver_comercial"). El
# orden acá es el orden de PRIORIDAD 2 del pedido del usuario, y define
# cuál dashboard queda de primero (auto-redirect si el rol solo tiene uno,
# ver layout_app.html: el tab de módulo enlaza a items[0].href).
_ITEMS_DASHBOARDS = [
    {"tabla": "comercial", "label": "Rendimiento comercial", "href": "/backoffice/dashboards/comercial", "icono": "bi-graph-up-arrow"},
    {"tabla": "finanzas", "label": "Control financiero", "href": "/backoffice/dashboards/finanzas", "icono": "bi-cash-stack"},
    {"tabla": "operaciones", "label": "Monitoreo de disrupciones", "href": "/backoffice/dashboards/disrupciones", "icono": "bi-exclamation-triangle"},
    {"tabla": "clientes", "label": "Captación y retención", "href": "/backoffice/dashboards/clientes", "icono": "bi-person-hearts"},
    {"tabla": "demanda", "label": "Demanda por producto", "href": "/backoffice/dashboards/demanda", "icono": "bi-bar-chart"},
    {"tabla": "paquetes", "label": "Paquetes y carrito", "href": "/backoffice/dashboards/paquetes", "icono": "bi-box-seam"},
    {"tabla": "catalogo_rutas", "label": "Catálogo y rutas", "href": "/backoffice/dashboards/catalogo-rutas", "icono": "bi-signpost-split"},
    {"tabla": "soporte", "label": "Calidad de soporte", "href": "/backoffice/dashboards/soporte", "icono": "bi-headset"},
    {"tabla": "campanas", "label": "Campañas y promociones", "href": "/backoffice/dashboards/campanas", "icono": "bi-envelope-paper"},
    {"tabla": "asistente_ia", "label": "Asistente IA", "href": "/backoffice/dashboards/asistente-ia", "icono": "bi-robot"},
    {"tabla": "alertas_precio", "label": "Alertas de precio", "href": "/backoffice/dashboards/alertas-precio", "icono": "bi-bell"},
    {"tabla": "agentes", "label": "Productividad del agente", "href": "/backoffice/dashboards/agentes", "icono": "bi-person-workspace"},
]

# Nivel estratégico (DS-00 a DS-03) — módulo dedicado `estrategico`, acceso
# uniforme (sin Nivel 2 por dashboard como "dashboards", ver
# scripts/seed_estrategico_rbac.py: hoy solo `Administrador` tiene "ver").
_ITEMS_ESTRATEGICO = [
    {"label": "Cockpit Ejecutivo", "href": "/backoffice/estrategico/cockpit", "icono": "bi-speedometer2"},
    {"label": "Rendimiento de la Oferta", "href": "/backoffice/estrategico/oferta", "icono": "bi-bar-chart-line"},
    {"label": "Gestión de Disrupciones", "href": "/backoffice/estrategico/disrupciones", "icono": "bi-exclamation-octagon"},
    {"label": "Inteligencia y Automatización", "href": "/backoffice/estrategico/inteligencia", "icono": "bi-cpu"},
]

MODULOS_CATALOGO = [
    {
        "clave": "seguridad",
        "nombre": "Seguridad",
        "icono": "bi-shield-lock",
        "items": [
            {"label": "Usuarios", "href": "/admin/usuarios", "icono": "bi-people"},
            {"label": "Roles", "href": "/admin/roles", "icono": "bi-diagram-3"},
            {"label": "Auditoría", "href": "/admin/auditoria", "icono": "bi-journal-text"},
            {"label": "Intentos fallidos", "href": "/admin/seguridad/intentos-fallidos", "icono": "bi-shield-exclamation"},
        ],
    },
    {
        "clave": "configuracion",
        "nombre": "Configuración",
        "icono": "bi-gear",
        "items": [
            {"label": "Política de contraseñas/sesión", "href": "/admin/configuracion", "icono": "bi-sliders"},
            {"label": "Métodos de pago", "href": "/admin/configuracion/metodos-pago", "icono": "bi-credit-card-2-front"},
            {"label": "Niveles de tarifa", "href": "/admin/configuracion/niveles-tarifa", "icono": "bi-layers"},
        ],
    },
    {
        "clave": "pasajeros",
        "nombre": "Pasajeros",
        "icono": "bi-person-badge",
        "items": [
            {"label": "Buscar pasajeros", "href": "/backoffice/pasajeros", "icono": "bi-search"},
            {"label": "Reporte de captación", "href": "/backoffice/pasajeros/reporte", "icono": "bi-graph-up"},
            {"label": "Programa de beneficios", "href": "/backoffice/programa-beneficios", "icono": "bi-award"},
        ],
    },
    {
        "clave": "vuelos_catalogo",
        "nombre": "Vuelos",
        "icono": "bi-airplane",
        "items": [
            {"label": "Catálogo de vuelos", "href": "/backoffice/vuelos", "icono": "bi-airplane"},
            {"label": "Aerolíneas", "href": "/backoffice/vuelos/aerolineas", "icono": "bi-building"},
            {"label": "Forzar estado (demo)", "href": "/backoffice/vuelos/forzar-estado", "icono": "bi-exclamation-diamond"},
            {"label": "Asientos y check-in", "href": "/backoffice/vuelos/config-asientos", "icono": "bi-grid-3x3-gap"},
            {"label": "Rotación Google Flights", "href": "/backoffice/vuelos/config-rotacion-cabina", "icono": "bi-arrow-repeat"},
            {"label": "Monitor DAG catálogo", "href": "/backoffice/vuelos/monitor-dag", "icono": "bi-diagram-3"},
            {"label": "Vuelos activos", "href": "/backoffice/vuelos/activos", "icono": "bi-broadcast"},
            {"label": "Catálogo publicado (MinIO)", "href": "/backoffice/vuelos/catalogo-publicado", "icono": "bi-cloud-check"},
        ],
    },
    {
        "clave": "reservas",
        "nombre": "Reservas",
        "icono": "bi-calendar-check",
        "items": [
            {"label": "Reserva asistida", "href": "/backoffice/reservas/nueva", "icono": "bi-headset"},
            {"label": "Reporte de reservas", "href": "/backoffice/reservas/reporte", "icono": "bi-graph-up"},
            {"label": "Mi cartera", "href": "/backoffice/reservas/mi-cartera", "icono": "bi-briefcase"},
            {"label": "Ítems por tipo de producto", "href": "/backoffice/reservas/items", "icono": "bi-boxes"},
        ],
    },
    {
        "clave": "disrupciones",
        "nombre": "Disrupciones",
        "icono": "bi-exclamation-triangle",
        "items": [
            {"label": "Gestión de disrupciones", "href": "/backoffice/disrupciones", "icono": "bi-exclamation-triangle"},
            {"label": "Notificaciones", "href": "/backoffice/notificaciones", "icono": "bi-bell"},
            {"label": "Umbral de risk score", "href": "/backoffice/disrupciones/config-riesgo", "icono": "bi-speedometer2"},
        ],
    },
    {
        "clave": "facturacion",
        "nombre": "Facturación",
        "icono": "bi-receipt",
        "items": [
            {"label": "Pagos", "href": "/backoffice/pagos", "icono": "bi-credit-card"},
            {"label": "Facturas", "href": "/backoffice/facturas", "icono": "bi-receipt"},
            {"label": "Comisiones", "href": "/backoffice/comisiones", "icono": "bi-percent"},
            {"label": "Remesas", "href": "/backoffice/remesas", "icono": "bi-bank"},
            {"label": "Pagos diferidos", "href": "/backoffice/pagos-diferidos", "icono": "bi-hourglass-split"},
            {"label": "Políticas de reembolso", "href": "/backoffice/politicas-reembolso", "icono": "bi-arrow-counterclockwise"},
            {"label": "Reembolsos", "href": "/backoffice/reembolsos", "icono": "bi-cash-coin"},
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
            {"label": "Ofertas destacadas", "href": "/backoffice/ofertas/destacadas", "icono": "bi-stars"},
            {"label": "Cupones", "href": "/backoffice/ofertas/cupones", "icono": "bi-ticket-perforated"},
            {"label": "Suscriptores newsletter", "href": "/backoffice/ofertas/suscriptores", "icono": "bi-envelope"},
            {"label": "Reporte de cupones", "href": "/backoffice/ofertas/reporte-cupones", "icono": "bi-graph-up"},
            {"label": "Campañas de email", "href": "/backoffice/ofertas/campanas", "icono": "bi-envelope-paper"},
            {"label": "Acumulación con paquete", "href": "/backoffice/ofertas/config-acumulacion-paquete", "icono": "bi-sliders"},
            {"label": "Reporte de favoritos", "href": "/backoffice/ofertas/reporte-favoritos", "icono": "bi-heart"},
        ],
    },
    {
        "clave": "paquetes",
        "nombre": "Paquetes",
        "icono": "bi-box-seam",
        "items": [
            {"label": "% Descuento por tipo", "href": "/backoffice/paquetes", "icono": "bi-percent"},
        ],
    },
    {
        "clave": "carrito",
        "nombre": "Carrito",
        "icono": "bi-cart3",
        "items": [
            {"label": "Configurar abandono", "href": "/backoffice/carrito/config-abandono", "icono": "bi-sliders"},
            {"label": "Reporte de recuperación", "href": "/backoffice/carrito/reporte", "icono": "bi-graph-up"},
        ],
    },
    {
        "clave": "autos",
        "nombre": "Autos",
        "icono": "bi-car-front",
        "items": [
            {"label": "Reporte por proveedor/categoría", "href": "/backoffice/autos/reporte", "icono": "bi-graph-up"},
        ],
    },
    {
        "clave": "proveedores",
        "nombre": "Proveedores comerciales",
        "icono": "bi-building",
        "items": [
            {"label": "Proveedores", "href": "/backoffice/proveedores", "icono": "bi-building"},
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
    {
        "clave": "dashboards",
        "nombre": "Dashboards",
        "icono": "bi-speedometer2",
        # `items` se completa por usuario en modulos_con_acceso() según el
        # Nivel 2 (tabla) de su rol — acá queda vacío a propósito, nunca se
        # usa este valor "de catálogo" tal cual para este módulo particular.
        "items": [],
    },
    {
        "clave": "estrategico",
        "nombre": "Estratégico",
        "icono": "bi-bullseye",
        # Sin Nivel 2 por dashboard (a diferencia de "dashboards") — el
        # rol que tiene "ver" en el módulo ve los 4 de una, así que acá sí
        # alcanza con la lista estática (ver _ITEMS_ESTRATEGICO arriba).
        "items": _ITEMS_ESTRATEGICO,
    },
]


CATEGORIAS_NAV = [
    {
        "clave": "sistema", "nombre": "Sistema", "icono": "bi-gear-wide-connected",
        "modulos": ["seguridad", "configuracion", "integraciones"],
    },
    {
        "clave": "clientes", "nombre": "Clientes", "icono": "bi-person-hearts",
        "modulos": ["pasajeros"],
    },
    {
        "clave": "catalogo_operacion", "nombre": "Catálogo y Operación", "icono": "bi-airplane",
        "modulos": ["vuelos_catalogo", "reservas", "disrupciones", "autos", "proveedores"],
    },
    {
        "clave": "comercial", "nombre": "Comercial", "icono": "bi-cash-coin",
        "modulos": ["facturacion", "ofertas", "paquetes", "carrito"],
    },
    {
        "clave": "soporte", "nombre": "Soporte", "icono": "bi-headset",
        "modulos": ["centro_ayuda", "asistente_ia"],
    },
]
# "dashboards" queda deliberadamente fuera de toda categoría — sus 11 ítems
# ya son en sí una lista plana de analítica (sin sub-módulos propios), así
# que se mantiene como su propio tab de primer nivel en vez de forzarlo
# dentro de una categoría paraguas (ver agrupar_por_categoria() más abajo).


def agrupar_por_categoria(nav_modulos: list[dict]) -> tuple[list[dict], dict | None, dict | None]:
    """Agrupa `nav_modulos` (ya filtrado por RBAC en modulos_con_acceso())
    en categorías "paraguas" para el mega menú del backoffice — agrupación
    puramente visual/de navegación, no cambia qué puede ver cada rol (eso
    ya lo decidió modulos_con_acceso(), esta función nunca agrega ni quita
    accesos). Ningún módulo se pierde: si un rol solo tiene acceso a 1 de
    los 3 módulos de "Sistema", la categoría igual aparece con esa única
    columna. Devuelve (categorías_con_al_menos_1_módulo, módulo_dashboards
    _o_None, módulo_estrategico_o_None) — dashboards/estrategico se manejan
    aparte porque no tienen sub-módulos, solo ítems (ver comentario arriba
    de CATEGORIAS_NAV)."""
    por_clave = {m["clave"]: m for m in nav_modulos}
    categorias = []
    for cat in CATEGORIAS_NAV:
        modulos_cat = [por_clave[clave] for clave in cat["modulos"] if clave in por_clave]
        if modulos_cat:
            categorias.append({**cat, "modulos": modulos_cat})
    dashboards = por_clave.get("dashboards")
    estrategico = por_clave.get("estrategico")
    return categorias, dashboards, estrategico


async def modulos_con_acceso(usuario: dict) -> list[dict]:
    """Módulos del catálogo sobre los que el rol del usuario tiene permiso
    Nivel 1 "ver". Pasajero es autoservicio, nunca ve grupos de backoffice
    acá — aunque su rol de sistema "Pasajero" tenga permisos "ver" propios
    (para las pantallas de autoservicio, no del backoffice), por eso se
    excluye por `tipo_actor` y no por ausencia de `rol_id` (obligatorio
    desde la migración 2026-07-27, ver rbac_service.py)."""
    if usuario.get("tipo_actor") == "pasajero":
        return []

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

    accesibles = [
        entry
        for entry in MODULOS_CATALOGO
        if (modulo_id := modulo_id_por_clave.get(entry["clave"]))
        and (permiso_id := permiso_ver_id_por_modulo_id.get(modulo_id))
        and permiso_id in permisos_del_rol
    ]

    # Copia por-request antes de personalizar "dashboards" — MODULOS_CATALOGO
    # es un módulo global compartido entre todas las requests/usuarios,
    # mutar sus dicts in-place filtraría los ítems de un usuario a otro.
    resultado = []
    for entry in accesibles:
        if entry["clave"] != "dashboards":
            resultado.append(entry)
            continue
        items_personalizados = [
            {"label": item["label"], "href": item["href"], "icono": item["icono"]}
            for item in _ITEMS_DASHBOARDS
            if await tiene_permiso(usuario, "dashboards", "ver", tabla=item["tabla"])
        ]
        if items_personalizados:
            resultado.append({**entry, "items": items_personalizados})

    return resultado


async def nav_context(usuario: dict) -> dict:
    nav_modulos = await modulos_con_acceso(usuario)
    nav_categorias, nav_dashboards, nav_estrategico = agrupar_por_categoria(nav_modulos)
    return {
        "usuario": usuario,
        "nav_modulos": nav_modulos,
        "nav_categorias": nav_categorias,
        "nav_dashboards": nav_dashboards,
        "nav_estrategico": nav_estrategico,
    }


async def primer_dashboard_accesible(usuario: dict) -> str | None:
    """Primer dashboard (Nivel 2 "ver" sobre el módulo "dashboards") al que
    el rol del usuario tiene acceso, en el mismo orden que el menú —
    usado por el login para mandar a cada rol de staff directo a su
    dashboard en vez de a un destino fijo. `None` si el rol no tiene
    ninguno (ej. admin_ti, fuera de la matriz de la spec de dashboards)."""
    for item in _ITEMS_DASHBOARDS:
        if await tiene_permiso(usuario, "dashboards", "ver", tabla=item["tabla"]):
            return item["href"]
    return None
