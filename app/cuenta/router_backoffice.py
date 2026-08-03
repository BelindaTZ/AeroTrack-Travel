"""CU-T24 — configurar el programa de beneficios (niveles, puntos por
dólar, vencimiento). Vive bajo el módulo "pasajeros" (Gestión de
Clientes) — no hay módulo "cuenta" propio en el catálogo de backoffice."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/programa-beneficios")


@router.get("")
async def listar_niveles(
    request: Request,
    mensaje: str | None = None,
    usuario: dict = Depends(requiere_permiso("pasajeros", "ver")),
):
    repo = CuentaRepository()
    niveles = await repo.niveles_programa_beneficios()

    contexto = await nav_context(usuario)
    contexto.update({"niveles": niveles, "mensaje": mensaje})
    return templates.TemplateResponse(request, "backoffice/programa_beneficios.html", contexto)


@router.post("/{nivel_id}")
async def actualizar_nivel(
    nivel_id: str,
    nombre_nivel: str = Form(...),
    puntos_minimos: float = Form(...),
    puntos_por_dolar: float = Form(...),
    vencimiento_meses: float = Form(...),
    beneficios: str = Form(""),
    usuario: dict = Depends(requiere_permiso("pasajeros", "editar")),
):
    repo = CuentaRepository()
    await repo.actualizar_nivel_beneficio(
        nivel_id,
        {
            "nombre_nivel": nombre_nivel,
            "puntos_minimos": puntos_minimos,
            "puntos_por_dolar": puntos_por_dolar,
            "vencimiento_meses": vencimiento_meses,
            "beneficios": beneficios,
        },
    )
    await AuditService().insertar(
        "actualizar_nivel_beneficio", "programa_beneficios_niveles",
        usuario_id=usuario["id"], registro_id=nivel_id,
    )
    return RedirectResponse("/backoffice/programa-beneficios?mensaje=Nivel actualizado", status_code=303)


@router.post("")
async def crear_nivel(
    nombre_nivel: str = Form(...),
    puntos_minimos: float = Form(...),
    puntos_por_dolar: float = Form(...),
    vencimiento_meses: float = Form(...),
    beneficios: str = Form(""),
    usuario: dict = Depends(requiere_permiso("pasajeros", "crear")),
):
    repo = CuentaRepository()
    nivel = await repo.crear_nivel_beneficio(
        {
            "nombre_nivel": nombre_nivel,
            "puntos_minimos": puntos_minimos,
            "puntos_por_dolar": puntos_por_dolar,
            "vencimiento_meses": vencimiento_meses,
            "beneficios": beneficios,
        }
    )
    await AuditService().insertar(
        "crear_nivel_beneficio", "programa_beneficios_niveles",
        usuario_id=usuario["id"], registro_id=nivel["id"],
    )
    return RedirectResponse("/backoffice/programa-beneficios?mensaje=Nivel creado", status_code=303)
