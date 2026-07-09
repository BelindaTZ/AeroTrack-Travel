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
        str(BASE_DIR / "app" / "shared" / "templates"),
    ]
)
