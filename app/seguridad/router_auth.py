"""RF-SEG-001,002,003 — login, logout, verificar sesión."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.auth_service import AuthService, CredencialesInvalidas, CuentaInactiva
from app.seguridad.services.session_service import COOKIE_NAME
from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client
from app.shared.templating import templates

router = APIRouter()

COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # vida del token de PocketBase (auth-refresh la renueva)


def _panel_por_rol(usuario: dict) -> str:
    tipo = usuario.get("tipo_actor")
    if tipo == "administrador":
        return "/admin/usuarios"
    return "/mi-perfil"


@router.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse(
        request, "login.html", {"next": request.query_params.get("next")}
    )


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str | None = Form(None),
):
    service = AuthService()
    audit = AuditService()
    ip = request.client.host if request.client else None

    try:
        resultado = await service.autenticar(email, password)
    except CredencialesInvalidas:
        await audit.insertar("login_fallido", "usuarios", detalle={"email": email}, ip=ip)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Credenciales incorrectas", "next": next},
            status_code=401,
        )
    except CuentaInactiva:
        await audit.insertar("login_fallido", "usuarios", detalle={"email": email, "motivo": "inactivo"}, ip=ip)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Cuenta desactivada. Contacte al administrador.", "next": next},
            status_code=403,
        )

    usuario = resultado["record"]
    await audit.insertar("login", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"], ip=ip)

    destino = next or _panel_por_rol(usuario)
    response = RedirectResponse(destino, status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        resultado["token"],
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE_SECONDS,
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            resultado = await get_pocketbase_client().auth_refresh("usuarios", token)
            await AuditService().insertar(
                "logout",
                "usuarios",
                usuario_id=resultado["record"]["id"],
                registro_id=resultado["record"]["id"],
                ip=request.client.host if request.client else None,
            )
        except PocketBaseError:
            pass  # token ya inválido/expirado: nada que auditar como logout explícito

    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
