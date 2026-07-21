"""RF-INT-001 (CU-T37) — configurar fuentes de datos externas."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.integraciones.services.integraciones_service import (
    CampoNoAplicaParaTipoUso,
    FuenteNoEncontrada,
    FuenteNoResincronizable,
    actualizar_fuente,
    listar_fuentes_con_cuota,
    resincronizar_fuente,
)
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/integraciones")


@router.get("/fuentes")
async def listar_fuentes(
    request: Request,
    usuario: dict = Depends(requiere_permiso("integraciones", "ver", "fuentes_datos_externas")),
):
    fuentes = await listar_fuentes_con_cuota()
    contexto = await nav_context(usuario)
    contexto.update({"fuentes": fuentes})
    return templates.TemplateResponse(request, "backoffice/fuentes.html", contexto)


@router.put("/fuentes/{fuente_id}")
async def actualizar_fuente_endpoint(
    fuente_id: str,
    activa: bool | None = Form(None),
    frecuencia_sincronizacion_horas: int | None = Form(None),
    usuario: dict = Depends(requiere_permiso("integraciones", "editar", "fuentes_datos_externas")),
):
    try:
        actualizada = await actualizar_fuente(
            fuente_id, activa=activa, frecuencia_sincronizacion_horas=frecuencia_sincronizacion_horas
        )
    except FuenteNoEncontrada:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    except CampoNoAplicaParaTipoUso as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    await AuditService().insertar(
        "actualizar_fuente", "fuentes_datos_externas", usuario_id=usuario["id"], registro_id=fuente_id
    )
    return actualizada


@router.post("/fuentes/{fuente_id}/resincronizar")
async def resincronizar_fuente_endpoint(
    fuente_id: str,
    usuario: dict = Depends(requiere_permiso("integraciones", "ejecutar", "fuentes_datos_externas")),
):
    try:
        await resincronizar_fuente(fuente_id, usuario["id"])
    except FuenteNoEncontrada:
        return RedirectResponse("/backoffice/integraciones/fuentes?mensaje=Fuente no encontrada", status_code=303)
    except FuenteNoResincronizable:
        return RedirectResponse(
            "/backoffice/integraciones/fuentes?mensaje=Esta fuente no admite resincronización manual",
            status_code=303,
        )

    await AuditService().insertar(
        "resincronizar_fuente", "fuentes_datos_externas", usuario_id=usuario["id"], registro_id=fuente_id
    )
    return RedirectResponse(
        "/backoffice/integraciones/fuentes?mensaje=Resincronización registrada — ver bitácora", status_code=303
    )
