"""RF-SEG-010,011,012 — crear/editar/eliminar rol."""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse

from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.seguridad.services.roles_service import (
    ACCIONES_NIVEL1,
    ACCIONES_NIVEL2,
    NivelDosExcedeNivelUno,
    RolConUsuariosAsignados,
    RolesService,
    RolProtegido,
)
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.pocketbase_client import get_pocketbase_client
from app.shared.templating import templates

router = APIRouter(prefix="/admin/roles")


async def _contexto_matriz(usuario: dict, rol_id: str):
    client = get_pocketbase_client()
    roles_service = RolesService(client=client)
    rol = await roles_service.obtener_rol(rol_id)
    matriz = await roles_service.matriz_actual(rol_id)
    modulos = (await client.list_records("modulos", {"perPage": 200, "sort": "orden"}))["items"]
    permisos = (await client.list_records("permisos", {"perPage": 500}))["items"]
    modulo_tablas = (await client.list_records("modulo_tablas", {"perPage": 500}))["items"]
    contexto = await nav_context(usuario)
    # (modulo_id, accion) con al menos una fila explícita de Nivel 2 — el resto
    # de las columnas están "sin restricción" (heredan Nivel 1 completo) y la
    # plantilla las muestra tildadas por defecto sin persistir nada hasta que
    # se toquen (ver perm-heredado en rol_editar.html).
    columnas_restringidas_nivel2 = {(m, a) for (m, _t, a) in matriz["tablas"]}

    contexto.update({
        "rol": rol,
        "modulos": modulos,
        "permisos": permisos,
        "modulo_tablas": modulo_tablas,
        "permiso_ids_actuales": matriz["permiso_ids"],
        "tablas_actuales": matriz["tablas"],
        "columnas_restringidas_nivel2": columnas_restringidas_nivel2,
        "acciones_nivel1": ACCIONES_NIVEL1,
        "acciones_nivel2": ACCIONES_NIVEL2,
    })
    return contexto


@router.get("")
async def listar(
    request: Request,
    nombre: str = Query(""),
    tipo_panel: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("seguridad", "ver", "roles")),
):
    roles = await RolesService().listar_roles(nombre=nombre or None, tipo_panel=tipo_panel or None)
    pagina = paginar(roles, page)
    contexto = await nav_context(usuario)
    contexto.update({"pagina": pagina, "filtros": {"nombre": nombre, "tipo_panel": tipo_panel}})
    return templates.TemplateResponse(request, "admin/roles.html", contexto)


@router.post("")
async def crear(
    nombre: str = Form(...),
    descripcion: str = Form(""),
    tipo_panel: str = Form(...),
    usuario: dict = Depends(requiere_permiso("seguridad", "crear", "roles")),
):
    creado = await RolesService().crear_rol(nombre, descripcion, tipo_panel)
    await AuditService().insertar("crear", "roles", usuario_id=usuario["id"], registro_id=creado["id"])
    return redirect_con_mensaje("/admin/roles", "Rol creado")


@router.get("/{rol_id}/editar")
async def editar_form(
    request: Request,
    rol_id: str,
    usuario: dict = Depends(requiere_permiso("seguridad", "editar", "roles")),
):
    return templates.TemplateResponse(
        request, "admin/rol_editar.html", await _contexto_matriz(usuario, rol_id)
    )


@router.put("/{rol_id}")
async def editar(
    rol_id: str,
    nombre: str | None = Form(None),
    descripcion: str | None = Form(None),
    permiso_id: list[str] = Form([]),
    tabla_nivel2: list[str] = Form([]),
    usuario: dict = Depends(requiere_permiso("seguridad", "editar", "roles")),
):
    tablas_nivel2 = [tuple(t.split("::", 2)) for t in tabla_nivel2 if t.count("::") == 2]
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
