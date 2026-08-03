"""RF-SEG-006,007,017 — perfil propio, cambiar contraseña, eliminación.

Nota de alcance: `pasajeros` (perfil extendido 1:1) es propiedad del módulo
Pasajeros, deliberadamente fuera de esta sesión — este router solo expone
los campos propios de `usuarios` (nombre_completo). Teléfono, dirección de
facturación, contacto de emergencia, etc. se incorporan cuando se
implemente Pasajeros.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.auth_service import AuthService, CredencialesInvalidas, CuentaInactiva
from app.seguridad.services.password_service import PasswordDebil, PasswordService
from app.seguridad.services.session_service import verificar_sesion
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter()

_MIME_TIPOS_VALIDOS = {"image/jpeg", "image/png", "image/webp"}
_TAMANIO_MAXIMO_BYTES = 5 * 1024 * 1024  # mismo límite que usuarios.foto_perfil en el esquema real


async def _contexto_perfil(usuario: dict, **extra) -> dict:
    contexto = await nav_context(usuario)
    rol_nombre = None
    if usuario.get("rol_id"):
        rol = await SeguridadRepository()._client.get_record("roles", usuario["rol_id"])
        rol_nombre = rol["nombre"]
    contexto["rol_nombre"] = rol_nombre

    # RF-PAS-002/005/006 — datos de contacto, documentos de viaje y viajeros
    # frecuentes solo existen para pasajero (agente/admin no tienen registro
    # en `pasajeros`); Pasajeros es dueño de esos datos, así que se importa
    # acá adentro (no al tope del módulo) para no crear una dependencia dura
    # de Seguridad -> Pasajeros en todos los usos de este archivo.
    if usuario.get("tipo_actor") == "pasajero":
        from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
        from app.pasajeros.services.pasajeros_service import listar_documentos, listar_viajeros_frecuentes

        pas_repo = PasajerosRepository()
        contexto["pasajero"] = await pas_repo.pasajero_de_usuario(usuario["id"])
        contexto["documentos_viaje"] = await listar_documentos(usuario)
        contexto["viajeros_frecuentes"] = await listar_viajeros_frecuentes(usuario)

    contexto.update(extra)
    return contexto


@router.get("/mi-perfil")
async def mi_perfil(request: Request, usuario: dict = Depends(verificar_sesion)):
    return templates.TemplateResponse(request, "mi_perfil.html", await _contexto_perfil(usuario))


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
        request, "mi_perfil.html", await _contexto_perfil(actualizado, mensaje="Perfil actualizado")
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
            await _contexto_perfil(usuario, error_password="La contraseña actual no es correcta"),
            status_code=400,
        )

    if password_nueva != confirmacion:
        return templates.TemplateResponse(
            request,
            "mi_perfil.html",
            await _contexto_perfil(usuario, error_password="Las contraseñas no coinciden"),
            status_code=400,
        )

    password_service = PasswordService()
    try:
        await password_service.validar_fortaleza(password_nueva)
    except PasswordDebil as exc:
        return templates.TemplateResponse(
            request, "mi_perfil.html", await _contexto_perfil(usuario, error_password=exc.motivo),
            status_code=400,
        )

    repo = SeguridadRepository()
    await repo.update_usuario(
        usuario["id"], {"password": password_nueva, "passwordConfirm": password_nueva}
    )
    await AuditService().insertar(
        "cambiar_password", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"]
    )
    return templates.TemplateResponse(
        request, "mi_perfil.html", await _contexto_perfil(usuario, mensaje="Contraseña actualizada")
    )


@router.post("/mi-perfil/foto")
async def mi_perfil_subir_foto(
    request: Request,
    foto: UploadFile,
    usuario: dict = Depends(verificar_sesion),
):
    contenido = await foto.read()
    error = None
    if foto.content_type not in _MIME_TIPOS_VALIDOS:
        error = "Formato no admitido — solo JPG, PNG o WEBP."
    elif len(contenido) > _TAMANIO_MAXIMO_BYTES:
        error = "La imagen supera el tamaño máximo de 5 MB."

    if error:
        return templates.TemplateResponse(
            request, "mi_perfil.html", await _contexto_perfil(usuario, error=error), status_code=400
        )

    repo = SeguridadRepository()
    actualizado = await repo.actualizar_foto(
        usuario["id"], foto.filename or "foto.jpg", contenido, foto.content_type
    )
    await AuditService().insertar(
        "editar", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"],
        detalle={"campos": ["foto_perfil"]},
    )
    return templates.TemplateResponse(
        request, "mi_perfil.html", await _contexto_perfil(actualizado, mensaje="Foto de perfil actualizada")
    )


@router.get("/mi-perfil/foto")
async def mi_perfil_ver_foto(usuario: dict = Depends(verificar_sesion)):
    if not usuario.get("foto_perfil"):
        raise HTTPException(status_code=404)
    repo = SeguridadRepository()
    contenido = await repo.descargar_foto(usuario["id"], usuario["foto_perfil"])
    media_type = {"png": "image/png", "webp": "image/webp"}.get(
        usuario["foto_perfil"].rsplit(".", 1)[-1].lower(), "image/jpeg"
    )
    return Response(content=contenido, media_type=media_type)


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
        await _contexto_perfil(
            usuario,
            mensaje=(
                "Tu solicitud de eliminación fue registrada. Se ejecutará una vez verificada "
                "la ausencia de reservas o pagos en curso."
            ),
        ),
    )
