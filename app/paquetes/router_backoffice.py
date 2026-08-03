"""CU-T14 — configurar % de descuento por tipo de paquete (combinación de
componentes). Actor: Administrador / admin_ventas."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.paquetes.repositories.paquetes_repo import PaquetesRepository
from app.paquetes.services.paquete_service import ORDEN_TIPOS, TIPOS_OBLIGATORIOS
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.nav import nav_context
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/paquetes")

# Combinaciones ofrecidas para crear — siempre con vuelo+hotel (RN-PAQ-001,
# los únicos obligatorios) más 0-2 opcionales, en el orden canónico de
# `paquete_service.combinacion_de` (ORDEN_TIPOS).
_OPCIONALES = [t for t in ORDEN_TIPOS if t not in TIPOS_OBLIGATORIOS]


def _combinaciones_disponibles() -> list[str]:
    combos = ["+".join(sorted(TIPOS_OBLIGATORIOS, key=ORDEN_TIPOS.index))]
    for extra in _OPCIONALES:
        combos.append("+".join(t for t in ORDEN_TIPOS if t in TIPOS_OBLIGATORIOS or t == extra))
    combos.append("+".join(ORDEN_TIPOS))  # todos los componentes
    return sorted(set(combos), key=lambda c: len(c.split("+")))


@router.get("")
async def listar(
    request: Request, usuario: dict = Depends(requiere_permiso("paquetes", "ver", "tipos_paquete_descuento"))
):
    combinaciones = await PaquetesRepository().listar_todas_combinaciones()
    existentes = {c["combinacion"] for c in combinaciones}
    contexto = await nav_context(usuario)
    contexto.update(
        {
            "combinaciones": combinaciones,
            "combinaciones_disponibles": [c for c in _combinaciones_disponibles() if c not in existentes],
        }
    )
    return templates.TemplateResponse(request, "backoffice/paquetes_descuentos.html", contexto)


@router.post("")
async def crear(
    request: Request,
    combinacion: str = Form(...),
    porcentaje_descuento: float = Form(...),
    usuario: dict = Depends(requiere_permiso("paquetes", "editar", "tipos_paquete_descuento")),
):
    if not (0 < porcentaje_descuento <= 100):
        return RedirectResponse(
            "/backoffice/paquetes?mensaje=El+porcentaje+debe+estar+entre+0+y+100", status_code=303
        )
    creado = await PaquetesRepository().crear_combinacion(combinacion, porcentaje_descuento, True)
    await AuditService().insertar(
        "crear", "tipos_paquete_descuento", usuario_id=usuario["id"], registro_id=creado["id"],
        detalle={"combinacion": combinacion, "porcentaje_descuento": porcentaje_descuento},
    )
    return RedirectResponse("/backoffice/paquetes?mensaje=Combinación+creada", status_code=303)


@router.post("/{combinacion_id}")
async def actualizar(
    combinacion_id: str,
    porcentaje_descuento: float = Form(...),
    activo: bool = Form(False),
    usuario: dict = Depends(requiere_permiso("paquetes", "editar", "tipos_paquete_descuento")),
):
    if not (0 < porcentaje_descuento <= 100):
        return RedirectResponse(
            "/backoffice/paquetes?mensaje=El+porcentaje+debe+estar+entre+0+y+100", status_code=303
        )
    await PaquetesRepository().actualizar_combinacion(combinacion_id, porcentaje_descuento, activo)
    await AuditService().insertar(
        "editar", "tipos_paquete_descuento", usuario_id=usuario["id"], registro_id=combinacion_id,
        detalle={"porcentaje_descuento": porcentaje_descuento, "activo": activo},
    )
    return RedirectResponse("/backoffice/paquetes?mensaje=Combinación+actualizada", status_code=303)
