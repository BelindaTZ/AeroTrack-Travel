"""RF-SEG-003 / CU-O42 — verificación de sesión activa, transversal.

`verificar_sesion` se expone como `Depends(...)` inyectable desde los otros
5 módulos: valida que el token exista, no haya expirado y corresponda a un
usuario activo, antes de que cualquier lógica de negocio se ejecute.
"""

from fastapi import Request

from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client

COOKIE_NAME = "pb_auth"


class SesionExpirada(Exception):
    """Token ausente, inválido, expirado, o usuario inactivo.

    No hereda de HTTPException para no acoplar este servicio transversal a
    un formato de respuesta particular — cada módulo (o `main.py`) decide
    cómo renderizar el rechazo vía un exception_handler.
    """

    def __init__(self, next_path: str | None = None):
        self.next_path = next_path
        super().__init__("Sesión inválida o expirada")


async def verificar_sesion(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    ruta_actual = request.url.path
    if request.url.query:
        ruta_actual += f"?{request.url.query}"

    if not token:
        raise SesionExpirada(next_path=ruta_actual)

    pb = get_pocketbase_client()
    try:
        resultado = await pb.auth_refresh("usuarios", token)
    except PocketBaseError:
        raise SesionExpirada(next_path=ruta_actual)

    usuario = resultado["record"]
    if not usuario.get("activo", False):
        raise SesionExpirada(next_path=ruta_actual)

    request.state.usuario = usuario
    request.state.pb_token = resultado["token"]
    return usuario
