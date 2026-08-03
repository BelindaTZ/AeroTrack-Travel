"""RF-SEG-009 — gestión de usuarios internos (backoffice).

WP-02 (auditoría de WorkPanels, 2026-07-31) — filtros (nombre, correo, rol,
estado), paginación, modal "Ver" y confirmación antes de desactivar. El
patrón de edición inline (rol/activo por fetch, sin recargar la página)
se mantiene — ya era un buen ajuste a J11 (feedback inmediato) antes de
esta auditoría, no había motivo para reemplazarlo por redirects.
"""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.plantillas_service import plantilla
from app.seguridad.services.rbac_service import requiere_permiso
from app.seguridad.services.roles_service import RolesService
from app.seguridad.services.usuarios_service import CorreoDuplicado, UsuariosService
from app.shared.email_sender import enviar_correo
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates

router = APIRouter(prefix="/admin/usuarios")


@router.get("")
async def listar(
    request: Request,
    nombre: str = Query(""),
    email: str = Query(""),
    rol_id: str = Query(""),
    estado: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("seguridad", "ver", "usuarios")),
):
    activo = {"activo": True, "inactivo": False}.get(estado)
    usuarios = await UsuariosService().listar_usuarios_internos(
        nombre=nombre or None, email=email or None, rol_id=rol_id or None, activo=activo
    )
    pagina = paginar(usuarios, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "roles": await RolesService().listar_roles(),
            "filtros": {"nombre": nombre, "email": email, "rol_id": rol_id, "estado": estado},
        }
    )
    return templates.TemplateResponse(request, "admin/usuarios.html", contexto)


@router.post("")
async def crear(
    nombre_completo: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    rol_id: str = Form(...),
    usuario: dict = Depends(requiere_permiso("seguridad", "crear", "usuarios")),
):
    try:
        creado = await UsuariosService().crear_usuario_interno(
            nombre_completo, email, password, rol_id
        )
    except CorreoDuplicado:
        return redirect_con_mensaje("/admin/usuarios", "Ese correo ya está registrado", tipo="error")

    await AuditService().insertar(
        "crear", "usuarios", usuario_id=usuario["id"], registro_id=creado["id"],
        detalle={"rol_id": rol_id},
    )
    return redirect_con_mensaje("/admin/usuarios", "Usuario creado")


@router.put("/{usuario_id}")
async def editar(
    usuario_id: str,
    nombre_completo: str | None = Form(None),
    rol_id: str | None = Form(None),
    activo: bool | None = Form(None),
    usuario: dict = Depends(requiere_permiso("seguridad", "editar", "usuarios")),
):
    actualizado = await UsuariosService().editar_usuario_interno(
        usuario_id, nombre_completo, rol_id, activo
    )
    campos = [
        nombre
        for nombre, valor in {
            "nombre_completo": nombre_completo,
            "rol_id": rol_id,
            "activo": activo,
        }.items()
        if valor is not None
    ]
    await AuditService().insertar(
        "editar",
        "usuarios",
        usuario_id=usuario["id"],
        registro_id=usuario_id,
        detalle={"campos": campos},
    )
    return JSONResponse(
        {
            "id": actualizado["id"],
            "activo": actualizado.get("activo"),
            "nombre_completo": actualizado.get("nombre_completo"),
        }
    )


@router.post("/{usuario_id}/resetear-password")
async def resetear_password(
    request: Request,
    usuario_id: str,
    usuario: dict = Depends(requiere_permiso("seguridad", "editar", "usuarios")),
):
    objetivo = await SeguridadRepository().get_usuario(usuario_id)
    token = await UsuariosService().resetear_password(usuario_id)
    enlace = str(request.url_for("restablecer_password_form", token=token))
    asunto = await plantilla("password_reset_admin.plantilla_asunto", "Restablecimiento de contraseña — AeroTrack Travel")
    cuerpo = await plantilla(
        "password_reset_admin.plantilla_cuerpo",
        "Un administrador inició un restablecimiento de tu contraseña. "
        "Usa este enlace (válido por tiempo limitado): {enlace}",
    )
    await enviar_correo(objetivo["email"], asunto, cuerpo.format(enlace=enlace))
    await AuditService().insertar(
        "resetear_password",
        "usuarios",
        usuario_id=usuario["id"],
        registro_id=usuario_id,
        detalle={"iniciado_por_admin": True},
    )
    return JSONResponse({"status": "enviado"})


@router.post("/{usuario_id}/cerrar-sesiones")
async def cerrar_sesiones(
    usuario_id: str,
    usuario: dict = Depends(requiere_permiso("seguridad", "editar", "usuarios")),
):
    """CU-T02 — fuerza el cierre de toda sesión activa de `usuario_id`."""
    await UsuariosService().cerrar_sesiones_activas(usuario_id)
    await AuditService().insertar(
        "cerrar_sesiones",
        "usuarios",
        usuario_id=usuario["id"],
        registro_id=usuario_id,
    )
    return JSONResponse({"status": "sesiones_cerradas"})
