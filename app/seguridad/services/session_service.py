"""RF-SEG-003 / CU-O42 — verificación de sesión activa, transversal.

`verificar_sesion` se expone como `Depends(...)` inyectable desde los otros
5 módulos: valida que el token exista, no haya expirado y corresponda a un
usuario activo, antes de que cualquier lógica de negocio se ejecute.
"""

from fastapi import Request

from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client

COOKIE_NAME = "pb_auth"


async def resolver_tipo_actor(rol_id: str | None) -> str:
    """Deriva "pasajero"/"agente"/"administrador" a partir del rol asignado.

    `usuarios` ya no tiene un campo `tipo_actor` propio (migración
    2026-07-27): a qué panel corresponde una cuenta es una propiedad del
    ROL (`roles.tipo_panel`), nunca algo que cada usuario fije aparte y que
    pudiera desalinearse de su rol real. Se llama en cada punto donde se
    resuelve una sesión (login, OAuth, `verificar_sesion`) para inyectar
    `usuario["tipo_actor"]` — así templates y redirects existentes siguen
    leyendo esa clave sin cambios, aunque ya no sea una columna persistida.
    "administrador" distingue por nombre del rol de sistema porque es
    puramente cosmético (badge de la topbar, destino de "/") — ya no
    autoriza nada (ver rbac_service.tiene_permiso)."""
    if not rol_id:
        return "pasajero"
    pb = get_pocketbase_client()
    rol = await pb.get_record("roles", rol_id)
    if rol.get("tipo_panel") != "backoffice":
        return "pasajero"
    return "administrador" if rol.get("nombre") == "Administrador" else "agente"


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

    usuario["tipo_actor"] = await resolver_tipo_actor(usuario.get("rol_id"))

    request.state.usuario = usuario
    request.state.pb_token = resultado["token"]
    return usuario


async def usuario_opcional(request: Request) -> dict | None:
    """Variante no-bloqueante de `verificar_sesion` para páginas del portal
    accesibles sin sesión (buscadores, carrito de invitado): resuelve el
    usuario si hay una cookie válida, o `None` si no la hay — nunca lanza
    `SesionExpirada`. Existe porque las páginas públicas necesitan saber
    "¿hay alguien logueado?" para pintar el topbar (nav, avatar, carrito)
    sin forzar el login."""
    try:
        return await verificar_sesion(request)
    except SesionExpirada:
        return None
