"""CU-T20 — configurar el umbral de risk score que dispara alerta
proactiva de disrupción (`riesgo_service.py` ya lo lee con fallback a
20.0 si no está sembrado)."""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.disrupciones.services.gestion_service import DisrupcionInvalida, resolver_disrupcion_manual
from app.disrupciones.services.riesgo_service import UMBRAL_RIESGO_PCT_DEFAULT
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates
from app.vuelos.repositories.vuelos_repo import VuelosRepository

router = APIRouter(prefix="/backoffice/disrupciones")

CLAVE_UMBRAL = "simulador_disrupciones.umbral_riesgo_pct"


@router.get("")
async def listar_disrupciones(
    request: Request,
    estado: str = Query(""),
    tipo_cambio: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("disrupciones", "ver")),
):
    repo = DisrupcionesRepository()
    disrupciones = await repo.listar_disrupciones(estado=estado or None, tipo_cambio=tipo_cambio or None)
    vuelos_repo = VuelosRepository()
    disrupciones_out = []
    for d in disrupciones:
        vuelo = await vuelos_repo.obtener_vuelo(d["vuelo_id"])
        disrupciones_out.append({**d, "vuelo": vuelo})
    pagina = paginar(disrupciones_out, page)

    contexto = await nav_context(usuario)
    contexto.update({"pagina": pagina, "filtros": {"estado": estado, "tipo_cambio": tipo_cambio}})
    return templates.TemplateResponse(request, "backoffice/disrupciones.html", contexto)


@router.post("/{disrupcion_id}/resolver")
async def resolver(disrupcion_id: str, usuario: dict = Depends(requiere_permiso("disrupciones", "editar"))):
    try:
        await resolver_disrupcion_manual(usuario, disrupcion_id)
    except DisrupcionInvalida as exc:
        return redirect_con_mensaje("/backoffice/disrupciones", str(exc), tipo="error")
    return redirect_con_mensaje("/backoffice/disrupciones", "Disrupción marcada como resuelta")


@router.get("/config-riesgo")
async def config_riesgo_form(
    request: Request,
    mensaje: str | None = None,
    usuario: dict = Depends(requiere_permiso("disrupciones", "ver")),
):
    repo = DisrupcionesRepository()
    registro = await repo.config(CLAVE_UMBRAL)
    umbral = registro["valor"] if registro else str(UMBRAL_RIESGO_PCT_DEFAULT)

    contexto = await nav_context(usuario)
    contexto.update({"umbral_riesgo_pct": umbral, "mensaje": mensaje})
    return templates.TemplateResponse(request, "backoffice/config_riesgo.html", contexto)


@router.post("/config-riesgo")
async def config_riesgo_submit(
    umbral_riesgo_pct: float = Form(...),
    usuario: dict = Depends(requiere_permiso("disrupciones", "editar")),
):
    repo = DisrupcionesRepository()
    registro = await repo.config(CLAVE_UMBRAL)
    if registro is None:
        await repo._client.create_record(
            "configuracion_sistema",
            {
                "clave": CLAVE_UMBRAL, "valor": str(umbral_riesgo_pct),
                "categoria": "simulador_disrupciones",
                "descripcion": "% de riesgo estimado a partir del cual se dispara alerta proactiva (CU-T20)",
                "modificado_por": usuario["id"],
            },
        )
    else:
        await repo.actualizar_config(CLAVE_UMBRAL, str(umbral_riesgo_pct))

    await AuditService().insertar(
        "configurar_umbral_riesgo", "configuracion_sistema", usuario_id=usuario["id"],
        detalle={"umbral_riesgo_pct": umbral_riesgo_pct},
    )
    return RedirectResponse(
        "/backoffice/disrupciones/config-riesgo?mensaje=Umbral actualizado", status_code=303
    )
