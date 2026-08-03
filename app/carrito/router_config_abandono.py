"""CU-T26 — configurar umbral de inactividad y plantilla del email de
recordatorio de carrito abandonado. Actor: Administrador."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.carrito.repositories.carrito_repo import CarritoRepository
from app.carrito.services.abandono_service import DEFAULT_ASUNTO, DEFAULT_CUERPO, DEFAULT_UMBRAL_HORAS
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/carrito")

_PERMISO_CONFIG = requiere_permiso("carrito", "editar", "carritos")


async def _contexto_config(usuario: dict, **extra) -> dict:
    repo = CarritoRepository()
    umbral = await repo.config("carrito_abandonado.umbral_horas_inactividad")
    asunto = await repo.config("carrito_abandonado.plantilla_asunto")
    cuerpo = await repo.config("carrito_abandonado.plantilla_cuerpo")
    contexto = await nav_context(usuario)
    contexto.update(
        {
            "umbral_horas": float(umbral["valor"]) if umbral else DEFAULT_UMBRAL_HORAS,
            "plantilla_asunto": asunto["valor"] if asunto else DEFAULT_ASUNTO,
            "plantilla_cuerpo": cuerpo["valor"] if cuerpo else DEFAULT_CUERPO,
        }
    )
    contexto.update(extra)
    return contexto


@router.get("/config-abandono")
async def config_abandono_form(request: Request, usuario: dict = Depends(_PERMISO_CONFIG)):
    contexto = await _contexto_config(usuario)
    return templates.TemplateResponse(request, "backoffice/config_abandono.html", contexto)


@router.post("/config-abandono")
async def config_abandono_submit(
    request: Request,
    umbral_horas: float = Form(...),
    plantilla_asunto: str = Form(...),
    plantilla_cuerpo: str = Form(...),
    usuario: dict = Depends(_PERMISO_CONFIG),
):
    if umbral_horas <= 0:
        contexto = await _contexto_config(usuario, error="El umbral de inactividad debe ser mayor a 0 horas.")
        return templates.TemplateResponse(request, "backoffice/config_abandono.html", contexto, status_code=400)
    if not plantilla_asunto.strip() or not plantilla_cuerpo.strip():
        contexto = await _contexto_config(usuario, error="El asunto y el cuerpo del email no pueden quedar vacíos.")
        return templates.TemplateResponse(request, "backoffice/config_abandono.html", contexto, status_code=400)

    repo = CarritoRepository()
    await repo.actualizar_config("carrito_abandonado.umbral_horas_inactividad", str(umbral_horas), usuario["id"])
    await repo.actualizar_config("carrito_abandonado.plantilla_asunto", plantilla_asunto.strip(), usuario["id"])
    await repo.actualizar_config("carrito_abandonado.plantilla_cuerpo", plantilla_cuerpo.strip(), usuario["id"])
    await AuditService().insertar(
        "editar",
        "configuracion_sistema",
        usuario_id=usuario["id"],
        detalle={"categoria": "carrito_abandonado", "umbral_horas": umbral_horas},
    )
    return RedirectResponse(
        "/backoffice/carrito/config-abandono?mensaje=Configuración+de+abandono+de+carrito+actualizada", status_code=303
    )
