"""RF-SEG-010,011,012 — crear/editar/eliminar rol."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse

from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.seguridad.services.roles_service import (
    NivelDosExcedeNivelUno,
    RolConUsuariosAsignados,
    RolesService,
    RolProtegido,
)
from app.shared.pocketbase_client import get_pocketbase_client
from app.shared.templating import templates

router = APIRouter(prefix="/admin/roles")


async def _contexto_matriz(rol_id: str):
    client = get_pocketbase_client()
    roles_service = RolesService(client=client)
    rol = await roles_service.obtener_rol(rol_id)
    matriz = await roles_service.matriz_actual(rol_id)
    modulos = (await client.list_records("modulos", {"perPage": 200, "sort": "orden"}))["items"]
    permisos = (await client.list_records("permisos", {"perPage": 500}))["items"]
    modulo_tablas = (await client.list_records("modulo_tablas", {"perPage": 500}))["items"]
    return {
        "rol": rol,
        "modulos": modulos,
        "permisos": permisos,
        "modulo_tablas": modulo_tablas,
        "permiso_ids_actuales": matriz["permiso_ids"],
        "tablas_actuales": matriz["tablas"],
    }


@router.get("")
async def listar(
    request: Request, usuario: dict = Depends(requiere_permiso("seguridad", "ver", "roles"))
):
    roles = await RolesService().listar_roles()
    return templates.TemplateResponse(request, "admin/roles.html", {"roles": roles})


@router.post("")
async def crear(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    usuario: dict = Depends(requiere_permiso("seguridad", "crear", "roles")),
):
    creado = await RolesService().crear_rol(nombre, descripcion)
    await AuditService().insertar("crear", "roles", usuario_id=usuario["id"], registro_id=creado["id"])
    roles = await RolesService().listar_roles()
    return templates.TemplateResponse(
        request, "admin/roles.html", {"roles": roles, "mensaje": "Rol creado"}
    )


@router.get("/{rol_id}/editar")
async def editar_form(
    request: Request,
    rol_id: str,
    usuario: dict = Depends(requiere_permiso("seguridad", "editar", "roles")),
):
    return templates.TemplateResponse(request, "admin/rol_editar.html", await _contexto_matriz(rol_id))


@router.put("/{rol_id}")
async def editar(
    rol_id: str,
    nombre: str | None = Form(None),
    descripcion: str | None = Form(None),
    permiso_id: list[str] = Form([]),
    tabla_nivel2: list[str] = Form([]),
    usuario: dict = Depends(requiere_permiso("seguridad", "editar", "roles")),
):
    tablas_nivel2 = [tuple(t.split("::", 1)) for t in tabla_nivel2 if "::" in t]
    try:
        actualizado = await RolesService().editar_rol(rol_id, nombre, descripcion, permiso_id, tablas_nivel2)
    except NivelDosExcedeNivelUno:
        return JSONResponse(
            status_code=400,
            content={"detail": "Nivel 2 no puede autorizar un módulo no autorizado en Nivel 1 (RN-SEG-009)"},
        )

    await AuditService().insertar(
        "editar",
        "roles",
        usuario_id=usuario["id"],
        registro_id=rol_id,
        detalle={"permisos_nivel1": len(permiso_id), "permisos_nivel2": len(tablas_nivel2)},
    )
    return JSONResponse({"id": actualizado["id"], "nombre": actualizado["nombre"]})


@router.delete("/{rol_id}")
async def eliminar(
    rol_id: str, usuario: dict = Depends(requiere_permiso("seguridad", "eliminar", "roles"))
):
    try:
        await RolesService().eliminar_rol(rol_id)
    except RolProtegido:
        return JSONResponse(status_code=409, content={"detail": "Rol protegido, no se puede eliminar"})
    except RolConUsuariosAsignados as exc:
        return JSONResponse(
            status_code=409,
            content={
                "detail": f"El rol tiene {exc.cantidad} usuario(s) activos asignados. "
                "Reasígnalos a otro rol antes de eliminar."
            },
        )

    await AuditService().insertar("eliminar", "roles", usuario_id=usuario["id"], registro_id=rol_id)
    return JSONResponse({"status": "eliminado"})
