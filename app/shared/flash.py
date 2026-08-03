"""Redirect con mensaje de feedback tipado — Fix global 2 de la auditoría de
WorkPanels (docs/workpanels-auditoria.md). Antes cada router armaba a mano
`RedirectResponse(f"...?mensaje={texto}")`, sin escapar la query string y
siempre con estilo de éxito (verde) en `layout_app.html`, sin importar si el
mensaje era en realidad un error de negocio.

Uso:

    from app.shared.flash import redirect_con_mensaje

    return redirect_con_mensaje("/backoffice/comisiones", "Comisión marcada como cobrada")
    return redirect_con_mensaje("/backoffice/comisiones", "Esa comisión ya estaba cobrada", tipo="error")

`tipo` es "exito" (default), "error" o "advertencia" — `layout_app.html` lee
`mensaje`/`tipo` de la query string y elige el color/ícono correspondiente
(ver `.flash-success`/`.flash-error`/`.flash-warning` en aerotrack.css).
"""

from typing import Literal
from urllib.parse import urlencode

from fastapi.responses import RedirectResponse

TipoMensaje = Literal["exito", "error", "advertencia"]


def redirect_con_mensaje(
    url_base: str, mensaje: str, tipo: TipoMensaje = "exito", status_code: int = 303
) -> RedirectResponse:
    separador = "&" if "?" in url_base else "?"
    query = urlencode({"mensaje": mensaje, "tipo": tipo})
    return RedirectResponse(f"{url_base}{separador}{query}", status_code=status_code)
