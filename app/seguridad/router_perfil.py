"""RF-SEG-006,007,017 — perfil propio, cambiar contraseña, eliminación.

Nota de alcance: `pasajeros` (perfil extendido 1:1) es propiedad del módulo
Pasajeros, deliberadamente fuera de esta sesión — este router solo expone
los campos propios de `usuarios` (nombre_completo). Teléfono, dirección de
facturación, contacto de emergencia, etc. se incorporan cuando se
implemente Pasajeros.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.auth_service import AuthService, CredencialesInvalidas, CuentaInactiva
from app.seguridad.services.password_service import PasswordDebil, PasswordService
from app.seguridad.services.session_service import verificar_sesion
from app.shared.templating import templates

router = APIRouter()


@router.get("/mi-perfil")
async def mi_perfil(request: Request, usuario: dict = Depends(verificar_sesion)):
    return templates.TemplateResponse(request, "mi_perfil.html", {"usuario": usuario})


@router.post("/mi-perfil")
async def mi_perfil_editar(
    request: Request,
    nombre_completo: str = Form(...),
    usuario: dict = Depends(verificar_sesion),
):
    repo = SeguridadRepository()
    actualizado = await repo.update_usuario(usuario["id"], {"nombre_completo": nombre_completo})
    await AuditService().insertar(
        "editar", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"],
        detalle={"campos": ["nombre_completo"]},
    )
    return templates.TemplateResponse(
        request, "mi_perfil.html", {"usuario": actualizado, "mensaje": "Perfil actualizado"}
    )


@router.post("/mi-perfil/cambiar-password")
async def cambiar_password(
    request: Request,
    password_actual: str = Form(...),
    password_nueva: str = Form(...),
    confirmacion: str = Form(...),
    usuario: dict = Depends(verificar_sesion),
):
    auth_service = AuthService()
    try:
        await auth_service.autenticar(usuario["email"], password_actual)
    except (CredencialesInvalidas, CuentaInactiva):
        return templates.TemplateResponse(
            request,
            "mi_perfil.html",
            {"usuario": usuario, "error_password": "La contraseña actual no es correcta"},
            status_code=400,
        )

    if password_nueva != confirmacion:
        return templates.TemplateResponse(
            request,
            "mi_perfil.html",
            {"usuario": usuario, "error_password": "Las contraseñas no coinciden"},
            status_code=400,
        )

    password_service = PasswordService()
    try:
        password_service.validar_fortaleza(password_nueva)
    except PasswordDebil as exc:
        return templates.TemplateResponse(
            request, "mi_perfil.html", {"usuario": usuario, "error_password": exc.motivo}, status_code=400
        )

    repo = SeguridadRepository()
    await repo.update_usuario(
        usuario["id"], {"password": password_nueva, "passwordConfirm": password_nueva}
    )
    await AuditService().insertar(
        "cambiar_password", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"]
    )
    return templates.TemplateResponse(
        request, "mi_perfil.html", {"usuario": usuario, "mensaje": "Contraseña actualizada"}
    )


@router.post("/mi-perfil/solicitar-eliminacion")
async def solicitar_eliminacion(request: Request, usuario: dict = Depends(verificar_sesion)):
    # RN-SEG-011: se debe retener el dato mientras existan reservas/pagos en
    # curso. Reservas y Facturación no existen todavía en esta sesión, así
    # que no hay retención que verificar aún — se registra la solicitud y se
    # informa que la ejecución efectiva depende de Pasajeros/Reservas.
    await AuditService().insertar(
        "solicitud_eliminacion_datos",
        "usuarios",
        usuario_id=usuario["id"],
        registro_id=usuario["id"],
        detalle={"estado": "registrada_pendiente_de_modulos_dependientes"},
    )
    return templates.TemplateResponse(
        request,
        "mi_perfil.html",
        {
            "usuario": usuario,
            "mensaje": (
                "Tu solicitud de eliminación fue registrada. Se ejecutará una vez verificada "
                "la ausencia de reservas o pagos en curso."
            ),
        },
    )
