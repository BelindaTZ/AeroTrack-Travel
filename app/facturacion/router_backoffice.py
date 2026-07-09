"""RF-FAC-004,005 (CU-O35,O36) — conciliación de comisiones y remesas."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.services.comision_service import (
    ComisionNoEncontrada,
    ComisionYaCobrada,
    marcar_cobrada,
)
from app.facturacion.services.remesa_service import SinComisionesParaRemesa, generar_remesa
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates
from app.vuelos.repositories.vuelos_repo import VuelosRepository

router = APIRouter(prefix="/backoffice")


@router.get("/comisiones")
async def listar_comisiones(
    request: Request,
    estado: str | None = None,
    aerolinea_id: str | None = None,
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "comisiones")),
):
    repo = FacturacionRepository()
    vuelos_repo = VuelosRepository()

    condiciones = []
    if estado:
        condiciones.append(f'estado="{estado}"')
    if aerolinea_id:
        condiciones.append(f'aerolinea_id="{aerolinea_id}"')
    filtro = " && ".join(condiciones) if condiciones else None

    comisiones = await repo.listar_comisiones(filtro)
    aerolineas = await vuelos_repo.listar_aerolineas_activas()
    nombre_por_id = {a["id"]: a["nombre"] for a in aerolineas}
    comisiones_out = [{**c, "aerolinea_nombre": nombre_por_id.get(c["aerolinea_id"], "")} for c in comisiones]

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "comisiones": comisiones_out,
            "aerolineas": aerolineas,
            "filtros": {"estado": estado or "", "aerolinea_id": aerolinea_id or ""},
        }
    )
    return templates.TemplateResponse(request, "backoffice/comisiones.html", contexto)


@router.post("/comisiones/{comision_id}/marcar-cobrada")
async def marcar_cobrada_endpoint(
    comision_id: str,
    usuario: dict = Depends(requiere_permiso("facturacion", "editar", "comisiones")),
):
    try:
        await marcar_cobrada(comision_id)
    except ComisionNoEncontrada:
        return RedirectResponse("/backoffice/comisiones?mensaje=Comisión no encontrada", status_code=303)
    except ComisionYaCobrada:
        return RedirectResponse(
            "/backoffice/comisiones?mensaje=Esa comisión ya estaba cobrada", status_code=303
        )

    await AuditService().insertar(
        "marcar_cobrada", "comisiones", usuario_id=usuario["id"], registro_id=comision_id
    )
    return RedirectResponse("/backoffice/comisiones?mensaje=Comisión marcada como cobrada", status_code=303)


@router.get("/remesas")
async def listar_remesas(
    request: Request,
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "remesas")),
):
    repo = FacturacionRepository()
    vuelos_repo = VuelosRepository()

    remesas = await repo.listar_remesas()
    aerolineas = await vuelos_repo.listar_aerolineas_activas()
    nombre_por_id = {a["id"]: a["nombre"] for a in aerolineas}
    remesas_out = [{**r, "aerolinea_nombre": nombre_por_id.get(r["aerolinea_id"], "")} for r in remesas]

    contexto = await nav_context(usuario)
    contexto.update({"remesas": remesas_out, "aerolineas": aerolineas})
    return templates.TemplateResponse(request, "backoffice/remesas.html", contexto)


@router.post("/remesas")
async def crear_remesa_endpoint(
    aerolinea_id: str = Form(...),
    periodo: str = Form(...),
    usuario: dict = Depends(requiere_permiso("facturacion", "crear", "remesas")),
):
    try:
        remesa = await generar_remesa(aerolinea_id, periodo)
    except SinComisionesParaRemesa:
        return RedirectResponse(
            "/backoffice/remesas?mensaje=No hay comisiones cobradas sin remesar para esa aerolínea",
            status_code=303,
        )

    await AuditService().insertar(
        "generar_remesa",
        "remesas",
        usuario_id=usuario["id"],
        registro_id=remesa["id"],
        detalle={"aerolinea_id": aerolinea_id, "periodo": periodo, "monto_total": remesa["monto_total"]},
    )
    return RedirectResponse("/backoffice/remesas?mensaje=Remesa generada", status_code=303)
