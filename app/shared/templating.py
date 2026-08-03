"""Instancia única de Jinja2Templates compartida por todos los routers.

Evita que cada módulo arme su propia lista de directorios de templates.
Cuando se agreguen los otros 5 módulos (vuelos, reservas, facturación, ...),
sus carpetas `templates/` se añaden aquí, no en cada router.
"""

from pathlib import Path
from urllib.parse import urlencode

from fastapi import Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def url_pagina(request: Request, pagina: int) -> str:
    """Reconstruye la URL actual cambiando solo `page` — usado por
    `_paginacion.html` para que los links de página conserven los filtros
    activos (estado, búsqueda, etc.) sin que cada WP tenga que armar la
    query string a mano."""
    params = dict(request.query_params)
    params["page"] = str(pagina)
    return f"{request.url.path}?{urlencode(params)}"


def url_exportar(request: Request, ruta_exportar: str) -> str:
    """Fix global (informes simples, sesión 2026-08-01) — arma la URL del
    botón "Exportar CSV" preservando los filtros activos (sin `page`, la
    exportación siempre trae todo lo filtrado, no solo la página actual)."""
    params = dict(request.query_params)
    params.pop("page", None)
    query = urlencode(params)
    return f"{ruta_exportar}?{query}" if query else ruta_exportar


templates = Jinja2Templates(
    directory=[
        str(BASE_DIR / "app" / "seguridad" / "templates"),
        str(BASE_DIR / "app" / "vuelos" / "templates"),
        str(BASE_DIR / "app" / "reservas" / "templates"),
        str(BASE_DIR / "app" / "facturacion" / "templates"),
        str(BASE_DIR / "app" / "pasajeros" / "templates"),
        str(BASE_DIR / "app" / "disrupciones" / "templates"),
        str(BASE_DIR / "app" / "integraciones" / "templates"),
        str(BASE_DIR / "app" / "autos" / "templates"),
        str(BASE_DIR / "app" / "actividades" / "templates"),
        str(BASE_DIR / "app" / "cruceros" / "templates"),
        str(BASE_DIR / "app" / "hoteles" / "templates"),
        str(BASE_DIR / "app" / "carrito" / "templates"),
        str(BASE_DIR / "app" / "paquetes" / "templates"),
        str(BASE_DIR / "app" / "proveedores" / "templates"),
        str(BASE_DIR / "app" / "cuenta" / "templates"),
        str(BASE_DIR / "app" / "centro_ayuda" / "templates"),
        str(BASE_DIR / "app" / "ofertas" / "templates"),
        str(BASE_DIR / "app" / "asistente_ia" / "templates"),
        str(BASE_DIR / "app" / "dashboards" / "templates"),
        str(BASE_DIR / "app" / "shared" / "templates"),
    ]
)
templates.env.globals["url_pagina"] = url_pagina
templates.env.globals["url_exportar"] = url_exportar
