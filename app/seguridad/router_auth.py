"""RF-SEG-001,002,003 — login, logout, verificar sesión."""

import json
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.auth_service import AuthService, CredencialesInvalidas, CuentaInactiva
from app.seguridad.services.session_service import COOKIE_NAME, resolver_tipo_actor
from app.shared.nav import primer_dashboard_accesible
from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client
from app.shared.templating import templates

router = APIRouter()

COOKIE_MAX_AGE_SECONDS_DEFAULT = 60 * 60 * 24 * 7  # default si no hay config (RNF-SEG-007)
GOOGLE_PENDING_COOKIE = "google_oauth_pending"
GOOGLE_PENDING_MAX_AGE_SECONDS = 600  # ventana para completar el consentimiento en Google


async def _duracion_sesion_segundos() -> int:
    """CU-T03 — duración de sesión configurable desde /admin/configuracion
    (clave `sesion.duracion_dias`); default de 7 días si no está seteada."""
    config = await SeguridadRepository().get_config("sesion.duracion_dias")
    if config is None:
        return COOKIE_MAX_AGE_SECONDS_DEFAULT
    try:
        return int(config["valor"]) * 60 * 60 * 24
    except (TypeError, ValueError):
        return COOKIE_MAX_AGE_SECONDS_DEFAULT


async def _panel_por_rol(usuario: dict) -> str:
    tipo = usuario.get("tipo_actor")
    if tipo == "pasajero":
        return "/"

    # Cualquier cuenta de staff (agente o administrador) entra directo a su
    # primer dashboard accesible — ya no tiene sentido un destino fijo
    # ("/mi-perfil"/"/admin/usuarios") ahora que existen los 13 dashboards
    # de la Fase C, uno por rol como mínimo (ver seed_dashboards_rbac.py).
    destino_dashboard = await primer_dashboard_accesible(usuario)
    if destino_dashboard:
        return destino_dashboard

    # Fallback para roles de staff sin ningún dashboard asignado todavía
    # (ej. admin_ti, fuera de la matriz de la spec de dashboards) — mismo
    # destino de siempre, para no dejarlos sin dónde aterrizar.
    return "/admin/usuarios" if tipo == "administrador" else "/mi-perfil"


@router.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "next": request.query_params.get("next"),
            "error": request.query_params.get("error"),
        },
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
    usuario["tipo_actor"] = await resolver_tipo_actor(usuario.get("rol_id"))
    await audit.insertar("login", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"], ip=ip)

    destino = next or await _panel_por_rol(usuario)
    response = RedirectResponse(destino, status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        resultado["token"],
        httponly=True,
        samesite="lax",
        max_age=await _duracion_sesion_segundos(),
    )
    return response


@router.get("/login/google")
async def login_google(request: Request):
    """RF-SEG-001 (Google) — arranca el flujo OAuth2 contra PocketBase.

    Autoregistro es exclusivo de pasajeros (solo un admin da de alta agentes
    u otros admins), así que este camino de login/registro nunca crea nada
    más que `tipo_actor: pasajero` — mismo criterio que /registro.
    """
    next_path = request.query_params.get("next")
    redirect_url = str(request.url_for("login_google_callback"))

    try:
        metodos = await get_pocketbase_client().list_auth_methods("usuarios")
    except PocketBaseError:
        return RedirectResponse(
            "/login?error=" + quote("Continuar con Google no está disponible en este momento."),
            status_code=303,
        )

    provider = next(
        (p for p in metodos.get("authProviders", []) if p.get("name") == "google"), None
    )
    if not provider:
        return RedirectResponse(
            "/login?error=" + quote("Continuar con Google no está disponible en este momento."),
            status_code=303,
        )

    response = RedirectResponse(provider["authUrl"] + quote(redirect_url, safe=""), status_code=303)
    response.set_cookie(
        GOOGLE_PENDING_COOKIE,
        json.dumps(
            {
                "state": provider["state"],
                "code_verifier": provider["codeVerifier"],
                "next": next_path,
            }
        ),
        httponly=True,
        samesite="lax",
        max_age=GOOGLE_PENDING_MAX_AGE_SECONDS,
    )
    return response


@router.get("/login/google/callback")
async def login_google_callback(request: Request):
    pendiente_raw = request.cookies.get(GOOGLE_PENDING_COOKIE)
    error_google = request.query_params.get("error")
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    def _volver_a_login(mensaje: str) -> RedirectResponse:
        resp = RedirectResponse("/login?error=" + quote(mensaje), status_code=303)
        resp.delete_cookie(GOOGLE_PENDING_COOKIE)
        return resp

    if error_google:
        return _volver_a_login("Inicio de sesión con Google cancelado.")
    if not pendiente_raw or not code or not state:
        return _volver_a_login("La solicitud de Google expiró o es inválida. Intenta de nuevo.")

    try:
        pendiente = json.loads(pendiente_raw)
    except ValueError:
        return _volver_a_login("La solicitud de Google expiró o es inválida. Intenta de nuevo.")

    if state != pendiente.get("state"):
        return _volver_a_login("La solicitud de Google expiró o es inválida. Intenta de nuevo.")

    redirect_url = str(request.url_for("login_google_callback"))
    audit = AuditService()
    ip = request.client.host if request.client else None

    pb = get_pocketbase_client()
    try:
        # `create_data` solo se usa si PocketBase crea la cuenta en este
        # mismo request (primer login con Google); en logins subsiguientes
        # se ignora porque el usuario ya existe. `rol_id` es obligatorio en
        # `usuarios` para los 3 tipos de actor (ver migración 2026-07-27),
        # así que hay que resolverlo aunque la mayoría de las veces no haga
        # falta.
        rol_pasajero = await pb.get_first("roles", 'nombre="Pasajero"')
        assert rol_pasajero is not None, "scripts/seed_seguridad.py debe correrse antes de operar"

        resultado = await pb.auth_with_oauth2(
            "usuarios",
            "google",
            code,
            pendiente["code_verifier"],
            redirect_url,
            create_data={
                "nombre_completo": "Cuenta de Google",
                "rol_id": rol_pasajero["id"],
            },
        )
    except PocketBaseError:
        await audit.insertar(
            "login_fallido", "usuarios", detalle={"metodo": "google"}, ip=ip
        )
        return _volver_a_login("No se pudo completar el inicio de sesión con Google.")

    usuario = resultado["record"]
    usuario["tipo_actor"] = await resolver_tipo_actor(usuario.get("rol_id"))
    if usuario.get("tipo_actor") != "pasajero":
        # Cuenta de staff (agente/admin) con este correo — Google no es su
        # método de acceso; no seguimos la sesión OAuth para esa cuenta.
        return _volver_a_login("Esta cuenta no usa inicio de sesión con Google.")

    meta = resultado.get("meta") or {}
    actualizaciones: dict = {}
    if meta.get("name") and usuario.get("nombre_completo") in (None, "", "Cuenta de Google"):
        actualizaciones["nombre_completo"] = meta["name"]

    repo_client = get_pocketbase_client()
    if actualizaciones:
        usuario = await repo_client.update_record(
            "usuarios", usuario["id"], actualizaciones, token=resultado["token"]
        )

    if meta.get("avatarUrl") and not usuario.get("foto_perfil"):
        try:
            async with httpx.AsyncClient() as descarga:
                foto_resp = await descarga.get(meta["avatarUrl"], timeout=10.0)
            if foto_resp.status_code == 200:
                usuario = await repo_client.update_record_con_archivo(
                    "usuarios",
                    usuario["id"],
                    {},
                    {"foto_perfil": ("google.jpg", foto_resp.content, "image/jpeg")},
                    token=resultado["token"],
                )
        except httpx.HTTPError:
            pass  # la foto de perfil es un extra, no bloquea el login

    # `update_record`/`update_record_con_archivo` arriba devuelven el registro
    # crudo de PocketBase (sin el `tipo_actor` inyectado) si hubo cambios de
    # nombre/foto — pero este punto del flujo solo se alcanza para pasajero
    # (la rama de staff ya retornó más arriba), así que es seguro fijarlo.
    usuario["tipo_actor"] = "pasajero"

    await audit.insertar(
        "login", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"],
        detalle={"metodo": "google"}, ip=ip,
    )

    destino = pendiente.get("next") or await _panel_por_rol(usuario)
    response = RedirectResponse(destino, status_code=303)
    response.delete_cookie(GOOGLE_PENDING_COOKIE)
    response.set_cookie(
        COOKIE_NAME,
        resultado["token"],
        httponly=True,
        samesite="lax",
        max_age=await _duracion_sesion_segundos(),
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
