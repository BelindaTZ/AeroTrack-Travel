"""Instancia única de Jinja2Templates compartida por todos los routers.

Evita que cada módulo arme su propia lista de directorios de templates.
Cuando se agreguen los otros 5 módulos (vuelos, reservas, facturación, ...),
sus carpetas `templates/` se añaden aquí, no en cada router.
"""

from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent.parent

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
        str(BASE_DIR / "app" / "cuenta" / "templates"),
        str(BASE_DIR / "app" / "centro_ayuda" / "templates"),
        str(BASE_DIR / "app" / "ofertas" / "templates"),
        str(BASE_DIR / "app" / "asistente_ia" / "templates"),
        str(BASE_DIR / "app" / "shared" / "templates"),
    ]
)
