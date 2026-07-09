"""RF-SEG-009 — gestión de usuarios internos (backoffice)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse

from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.seguridad.services.roles_service import RolesService
from app.seguridad.services.usuarios_service import CorreoDuplicado, UsuariosService
from app.shared.templating import templates

router = APIRouter(prefix="/admin/usuarios")


async def _contexto_lista(**extra):
    return {
        "usuarios": await UsuariosService().listar_usuarios_internos(),
        "roles": await RolesService().listar_roles(),
        **extra,
    }


@router.get("")
async def listar(
    request: Request, usuario: dict = Depends(requiere_permiso("seguridad", "ver", "usuarios"))
):
    return templates.TemplateResponse(request, "admin/usuarios.html", await _contexto_lista())


@router.post("")
async def crear(
    request: Request,
    nombre_completo: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    tipo_actor: str = Form(...),
    rol_id: str = Form(...),
    usuario: dict = Depends(requiere_permiso("seguridad", "crear", "usuarios")),
):
    try:
        creado = await UsuariosService().crear_usuario_interno(
            nombre_completo, email, password, tipo_actor, rol_id
        )
    except CorreoDuplicado:
        return templates.TemplateResponse(
            request,
            "admin/usuarios.html",
            await _contexto_lista(error="Ese correo ya está registrado"),
            status_code=409,
        )

    await AuditService().insertar(
        "crear",
        "usuarios",
        usuario_id=usuario["id"],
        registro_id=creado["id"],
        detalle={"tipo_actor": tipo_actor, "rol_id": rol_id},
    )
    return templates.TemplateResponse(
        request, "admin/usuarios.html", await _contexto_lista(mensaje="Usuario creado")
    )


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
    return JSONResponse({"id": actualizado["id"], "activo": actualizado.get("activo")})
