"""RF-VUE-006 (CU-O48) — ajuste puntual excepcional, solo para demo.

Incluye obligatoriamente verificación de sesión (CU-O42), RBAC (CU-O43) y
auditoría (CU-O41) — primer consumidor real, fuera de Seguridad, de los 3
servicios transversales.
"""

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse

from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.estado_service import ESTADOS_VALIDOS, EstadoInvalido
from app.vuelos.services.forzar_estado_service import MotivoRequerido, es_disrupcion, forzar_estado

router = APIRouter(prefix="/backoffice/vuelos")


@router.get("/forzar-estado")
async def forzar_estado_form(
    request: Request,
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "editar", "vuelos_catalogo")),
):
    repo = VuelosRepository()
    vuelos = await repo.listar_para_selector()
    contexto = await nav_context(usuario)
    contexto.update({"vuelos_json": json.dumps(vuelos), "estados": sorted(ESTADOS_VALIDOS)})
    return templates.TemplateResponse(request, "backoffice/forzar_estado.html", contexto)


@router.post("/{vuelo_id}/forzar-estado")
async def forzar_estado_submit(
    vuelo_id: str,
    nuevo_estado: str = Form(...),
    motivo: str = Form(...),
    usuario: dict = Depends(requiere_permiso("vuelos_catalogo", "editar", "vuelos_catalogo")),
):
    try:
        actualizado = await forzar_estado(vuelo_id, nuevo_estado, motivo)
    except MotivoRequerido:
        return JSONResponse(
            status_code=400,
            content={"detail": "El motivo es obligatorio para forzar un ajuste (RN-VUE-006)"},
        )
    except EstadoInvalido as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    detalle = {"motivo": motivo, "origen": "demo"}
    if es_disrupcion(nuevo_estado):
        # Disrupciones no existe todavía en esta sesión — se documenta la
        # intención en vez de simular un disparo real (ver errores-conocidos.md).
        detalle["notificacion"] = "pendiente_de_modulo_disrupciones"

    await AuditService().insertar(
        "forzar_estado",
        "vuelos_catalogo",
        usuario_id=usuario["id"],
        registro_id=vuelo_id,
        detalle=detalle,
    )
    return JSONResponse({"id": actualizado["id"], "estado": actualizado["estado"]})
