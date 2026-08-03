"""RF-SEG-004,005 — recuperar/restablecer contraseña."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.password_service import PasswordDebil, PasswordService, TokenInvalido
from app.seguridad.services.plantillas_service import plantilla
from app.shared.email_sender import enviar_correo
from app.shared.templating import templates

router = APIRouter()

MENSAJE_GENERICO = (
    "Si el correo está registrado, recibirás un enlace de recuperación en unos minutos."
)


@router.get("/recuperar-password")
async def recuperar_password_form(request: Request):
    return templates.TemplateResponse(request, "recuperar_password.html", {})


@router.post("/recuperar-password")
async def recuperar_password_submit(request: Request, email: str = Form(...)):
    repo = SeguridadRepository()
    password_service = PasswordService(repo)

    # RN-SEG-003: la respuesta al usuario es siempre la misma, exista o no
    # el correo. Solo si existe y está activa se genera el enlace real.
    usuario = await repo.get_usuario_by_email(email)
    if usuario is not None and usuario.get("activo", False):
        token = await password_service.generar_token_recuperacion(usuario["id"])
        enlace = str(request.url_for("restablecer_password_form", token=token))
        asunto = await plantilla("password_recovery.plantilla_asunto", "Recuperación de contraseña — AeroTrack Travel")
        cuerpo = await plantilla(
            "password_recovery.plantilla_cuerpo",
            "Usa este enlace para restablecer tu contraseña (válido por tiempo limitado): {enlace}",
        )
        await enviar_correo(email, asunto, cuerpo.format(enlace=enlace))
        await AuditService().insertar(
            "solicitud_recuperacion_password", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"]
        )

    return templates.TemplateResponse(
        request, "recuperar_password.html", {"mensaje": MENSAJE_GENERICO}
    )


@router.get("/restablecer-password/{token}", name="restablecer_password_form")
async def restablecer_password_form(request: Request, token: str):
    password_service = PasswordService()
    try:
        await password_service.validar_token(token)
    except TokenInvalido:
        return templates.TemplateResponse(request, "restablecer_password.html", {"token_invalido": True})
    return templates.TemplateResponse(request, "restablecer_password.html", {"token": token})


@router.post("/restablecer-password/{token}")
async def restablecer_password_submit(
    request: Request,
    token: str,
    password: str = Form(...),
    confirmacion: str = Form(...),
):
    password_service = PasswordService()

    try:
        usuario = await password_service.validar_token(token)
    except TokenInvalido:
        return templates.TemplateResponse(request, "restablecer_password.html", {"token_invalido": True})

    if password != confirmacion:
        return templates.TemplateResponse(
            request,
            "restablecer_password.html",
            {"token": token, "error": "Las contraseñas no coinciden"},
            status_code=400,
        )

    try:
        await password_service.validar_fortaleza(password)
    except PasswordDebil as exc:
        return templates.TemplateResponse(
            request, "restablecer_password.html", {"token": token, "error": exc.motivo}, status_code=400
        )

    await password_service.consumir_token(usuario["id"], password)
    await AuditService().insertar(
        "restablecer_password", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"]
    )

    return RedirectResponse(
        "/login?mensaje=Contraseña actualizada. Ya puedes iniciar sesión.", status_code=303
    )
