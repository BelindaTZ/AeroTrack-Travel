"""CU-T03 — configurar política de contraseñas y duración de sesión.
Actor: Administrador / admin_ti."""

from fastapi import APIRouter, Depends, Form, Query, Request

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.services.metodos_pago_service import (
    MetodoPagoInvalido,
    actualizar_metodo_pago,
    alternar_activo_metodo_pago,
    crear_metodo_pago,
)
from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.password_service import DEFAULT_MIN_LENGTH, DEFAULT_REQUIERE_NUMERO
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.niveles_tarifa_service import (
    NivelTarifaInvalido,
    actualizar_nivel_tarifa,
    crear_nivel_tarifa,
)

router = APIRouter(prefix="/admin/configuracion")

DEFAULT_DURACION_SESION_DIAS = 7


async def _contexto(usuario: dict) -> dict:
    repo = SeguridadRepository()
    min_length = await repo.get_config("password.min_length")
    requiere_numero = await repo.get_config("password.requiere_numero")
    duracion_sesion = await repo.get_config("sesion.duracion_dias")
    contexto = await nav_context(usuario)
    contexto.update(
        {
            "min_length": int(min_length["valor"]) if min_length else DEFAULT_MIN_LENGTH,
            "requiere_numero": (requiere_numero["valor"] not in ("false", "0", "")) if requiere_numero else DEFAULT_REQUIERE_NUMERO,
            "duracion_sesion_dias": int(duracion_sesion["valor"]) if duracion_sesion else DEFAULT_DURACION_SESION_DIAS,
            "plantillas": await repo.listar_config_por_categoria("plantilla_notificacion"),
            "feature_flags": await repo.listar_config_por_categoria("feature_flag"),
            "parametros": await repo.listar_config_por_categoria("parametro_negocio"),
        }
    )
    return contexto


@router.get("")
async def form(
    request: Request, usuario: dict = Depends(requiere_permiso("configuracion", "ver"))
):
    return templates.TemplateResponse(request, "admin/configuracion.html", await _contexto(usuario))


@router.post("")
async def submit(
    min_length: int = Form(...),
    requiere_numero: bool = Form(False),
    duracion_sesion_dias: int = Form(...),
    usuario: dict = Depends(requiere_permiso("configuracion", "editar")),
):
    if min_length < 6:
        return redirect_con_mensaje(
            "/admin/configuracion", "La longitud mínima no puede ser menor a 6 caracteres.", tipo="error"
        )
    if duracion_sesion_dias < 1:
        return redirect_con_mensaje(
            "/admin/configuracion", "La duración de sesión debe ser de al menos 1 día.", tipo="error"
        )

    repo = SeguridadRepository()
    await repo.actualizar_config("password.min_length", str(min_length), usuario["id"])
    await repo.actualizar_config("password.requiere_numero", "true" if requiere_numero else "false", usuario["id"])
    await repo.actualizar_config("sesion.duracion_dias", str(duracion_sesion_dias), usuario["id"])
    await AuditService().insertar(
        "editar",
        "configuracion_sistema",
        usuario_id=usuario["id"],
        detalle={"categoria": "politica_contrasenas", "min_length": min_length, "duracion_sesion_dias": duracion_sesion_dias},
    )
    return redirect_con_mensaje("/admin/configuracion", "Configuración actualizada")


# ── WP-08 (ampliación de sesión 2026-08-01) — plantillas de notificación,
# feature flags y parámetros de negocio, todos filas de
# `configuracion_sistema` agrupadas por categoría ─────────────────────────

@router.post("/plantillas/{config_id}")
async def editar_plantilla(
    config_id: str,
    valor: str = Form(...),
    usuario: dict = Depends(requiere_permiso("configuracion", "editar")),
):
    await SeguridadRepository().actualizar_config_por_id(config_id, valor, usuario["id"])
    await AuditService().insertar(
        "editar_plantilla_notificacion", "configuracion_sistema", usuario_id=usuario["id"], registro_id=config_id
    )
    return redirect_con_mensaje("/admin/configuracion", "Plantilla actualizada")


@router.post("/parametros/{config_id}")
async def editar_parametro(
    config_id: str,
    valor: str = Form(...),
    usuario: dict = Depends(requiere_permiso("configuracion", "editar")),
):
    await SeguridadRepository().actualizar_config_por_id(config_id, valor, usuario["id"])
    await AuditService().insertar(
        "editar_parametro_negocio", "configuracion_sistema", usuario_id=usuario["id"], registro_id=config_id
    )
    return redirect_con_mensaje("/admin/configuracion", "Parámetro actualizado")


@router.post("/flags")
async def crear_flag(
    clave: str = Form(...),
    descripcion: str = Form(""),
    valor: str = Form("false"),
    usuario: dict = Depends(requiere_permiso("configuracion", "editar")),
):
    repo = SeguridadRepository()
    if await repo.get_config(clave) is not None:
        return redirect_con_mensaje("/admin/configuracion", "Ya existe un feature flag con esa clave", tipo="error")
    await repo.crear_config(clave, "true" if valor == "true" else "false", "feature_flag", descripcion, usuario["id"])
    await AuditService().insertar(
        "crear_feature_flag", "configuracion_sistema", usuario_id=usuario["id"], detalle={"clave": clave}
    )
    return redirect_con_mensaje("/admin/configuracion", "Feature flag creado")


@router.post("/flags/{config_id}/alternar")
async def alternar_flag(
    config_id: str,
    usuario: dict = Depends(requiere_permiso("configuracion", "editar")),
):
    repo = SeguridadRepository()
    actual = await repo.get_config_por_id(config_id)
    if actual is None:
        return redirect_con_mensaje("/admin/configuracion", "Feature flag no encontrado", tipo="error")
    nuevo_valor = "false" if actual["valor"].strip().lower() != "false" else "true"
    await repo.actualizar_config_por_id(config_id, nuevo_valor, usuario["id"])
    await AuditService().insertar(
        "alternar_feature_flag", "configuracion_sistema", usuario_id=usuario["id"], registro_id=config_id,
        detalle={"valor": nuevo_valor},
    )
    mensaje = "Feature flag activado" if nuevo_valor == "true" else "Feature flag desactivado"
    return redirect_con_mensaje("/admin/configuracion", mensaje)


# ── WP-18 (auditoría de WorkPanels, 2026-08-01) — métodos de pago y
# niveles de tarifa, mismo módulo "Configuración" que el resto de esta
# página pero con su propia pantalla (catálogos con más de 3-4 filas) ────

@router.get("/metodos-pago")
async def listar_metodos_pago(
    request: Request,
    nombre: str = Query(""),
    estado: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("configuracion", "ver", "metodos_pago")),
):
    metodos = await FacturacionRepository().listar_metodos_pago(nombre=nombre or None, estado=estado or None)
    pagina = paginar(metodos, page)
    contexto = await nav_context(usuario)
    contexto.update({"pagina": pagina, "filtros": {"nombre": nombre, "estado": estado}})
    return templates.TemplateResponse(request, "admin/metodos_pago.html", contexto)


@router.post("/metodos-pago")
async def crear_metodo_pago_endpoint(
    nombre: str = Form(...),
    tipo: str = Form(...),
    procesador: str = Form(...),
    usuario: dict = Depends(requiere_permiso("configuracion", "editar", "metodos_pago")),
):
    await crear_metodo_pago(usuario, {"nombre": nombre, "tipo": tipo, "procesador": procesador, "activo": True})
    return redirect_con_mensaje("/admin/configuracion/metodos-pago", "Método de pago creado")


@router.post("/metodos-pago/{metodo_id}")
async def editar_metodo_pago_endpoint(
    metodo_id: str,
    nombre: str = Form(...),
    tipo: str = Form(...),
    procesador: str = Form(...),
    usuario: dict = Depends(requiere_permiso("configuracion", "editar", "metodos_pago")),
):
    try:
        await actualizar_metodo_pago(usuario, metodo_id, {"nombre": nombre, "tipo": tipo, "procesador": procesador})
    except MetodoPagoInvalido as exc:
        return redirect_con_mensaje("/admin/configuracion/metodos-pago", str(exc), tipo="error")
    return redirect_con_mensaje("/admin/configuracion/metodos-pago", "Método de pago actualizado")


@router.post("/metodos-pago/{metodo_id}/alternar-activo")
async def alternar_metodo_pago_endpoint(
    metodo_id: str,
    usuario: dict = Depends(requiere_permiso("configuracion", "editar", "metodos_pago")),
):
    try:
        actualizado = await alternar_activo_metodo_pago(usuario, metodo_id)
    except MetodoPagoInvalido as exc:
        return redirect_con_mensaje("/admin/configuracion/metodos-pago", str(exc), tipo="error")
    mensaje = "Método de pago reactivado" if actualizado["activo"] else "Método de pago desactivado"
    return redirect_con_mensaje("/admin/configuracion/metodos-pago", mensaje)


@router.get("/niveles-tarifa")
async def listar_niveles_tarifa(
    request: Request,
    usuario: dict = Depends(requiere_permiso("configuracion", "ver", "niveles_tarifa")),
):
    repo = VuelosRepository()
    niveles = await repo.listar_niveles_tarifa()
    politicas = await FacturacionRepository().listar_politicas_reembolso()
    politica_por_id = {p["id"]: p["nombre"] for p in politicas}
    niveles_out = [{**n, "politica_nombre": politica_por_id.get(n.get("politica_reembolso_id"), "—")} for n in niveles]
    contexto = await nav_context(usuario)
    contexto.update({"niveles": niveles_out, "politicas": politicas})
    return templates.TemplateResponse(request, "admin/niveles_tarifa.html", contexto)


@router.post("/niveles-tarifa")
async def crear_nivel_tarifa_endpoint(
    nombre: str = Form(...),
    descripcion: str = Form(""),
    politica_reembolso_id: str = Form(...),
    equipaje_incluido: bool = Form(False),
    cambios_permitidos: bool = Form(False),
    seleccion_asiento_temprana: bool = Form(False),
    usuario: dict = Depends(requiere_permiso("configuracion", "editar", "niveles_tarifa")),
):
    data = {
        "nombre": nombre, "descripcion": descripcion or None, "politica_reembolso_id": politica_reembolso_id,
        "equipaje_incluido": equipaje_incluido, "cambios_permitidos": cambios_permitidos,
        "seleccion_asiento_temprana": seleccion_asiento_temprana,
    }
    await crear_nivel_tarifa(usuario, data)
    return redirect_con_mensaje("/admin/configuracion/niveles-tarifa", "Nivel de tarifa creado")


@router.post("/niveles-tarifa/{nivel_id}")
async def editar_nivel_tarifa_endpoint(
    nivel_id: str,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    politica_reembolso_id: str = Form(...),
    equipaje_incluido: bool = Form(False),
    cambios_permitidos: bool = Form(False),
    seleccion_asiento_temprana: bool = Form(False),
    usuario: dict = Depends(requiere_permiso("configuracion", "editar", "niveles_tarifa")),
):
    data = {
        "nombre": nombre, "descripcion": descripcion or None, "politica_reembolso_id": politica_reembolso_id,
        "equipaje_incluido": equipaje_incluido, "cambios_permitidos": cambios_permitidos,
        "seleccion_asiento_temprana": seleccion_asiento_temprana,
    }
    try:
        await actualizar_nivel_tarifa(usuario, nivel_id, data)
    except NivelTarifaInvalido as exc:
        return redirect_con_mensaje("/admin/configuracion/niveles-tarifa", str(exc), tipo="error")
    return redirect_con_mensaje("/admin/configuracion/niveles-tarifa", "Nivel de tarifa actualizado")
