"""WP-10 (auditoría de WorkPanels, 2026-07-31) — gestión de proveedores
comerciales (`proveedores_comerciales`). Actor: admin_ventas, Administrador."""

from fastapi import APIRouter, Depends, Form, Query, Request

from app.proveedores.repositories.proveedores_repo import ProveedoresRepository
from app.proveedores.services.proveedores_service import (
    ProveedorInvalido,
    actualizar_proveedor,
    alternar_activo_proveedor,
    crear_proveedor,
)
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/proveedores")


async def _rbac_ver(usuario: dict = Depends(requiere_permiso("proveedores", "ver"))):
    return usuario


async def _rbac_crear(usuario: dict = Depends(requiere_permiso("proveedores", "crear"))):
    return usuario


async def _rbac_editar(usuario: dict = Depends(requiere_permiso("proveedores", "editar"))):
    return usuario


@router.get("")
async def listar(
    request: Request,
    nombre: str = Query(""),
    tipo_producto: str = Query(""),
    estado: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(_rbac_ver),
):
    proveedores = await ProveedoresRepository().listar(
        nombre=nombre or None, tipo_producto=tipo_producto or None, estado=estado or None
    )
    pagina = paginar(proveedores, page)
    contexto = await nav_context(usuario)
    contexto.update(
        {"pagina": pagina, "filtros": {"nombre": nombre, "tipo_producto": tipo_producto, "estado": estado}}
    )
    return templates.TemplateResponse(request, "backoffice/proveedores.html", contexto)


@router.post("")
async def crear(
    nombre: str = Form(...),
    tipo_producto: str = Form(...),
    comision_pactada_pct: str = Form(""),
    contacto: str = Form(""),
    fecha_contrato: str = Form(""),
    usuario: dict = Depends(_rbac_crear),
):
    data = {
        "nombre": nombre, "tipo_producto": tipo_producto,
        "comision_pactada_pct": float(comision_pactada_pct) if comision_pactada_pct.strip() else None,
        "contacto": contacto or None,
        "fecha_contrato": fecha_contrato or None,
        "activo": True,
    }
    await crear_proveedor(usuario, data)
    return redirect_con_mensaje("/backoffice/proveedores", "Proveedor creado")


@router.post("/{proveedor_id}")
async def editar(
    proveedor_id: str,
    nombre: str = Form(...),
    tipo_producto: str = Form(...),
    comision_pactada_pct: str = Form(""),
    contacto: str = Form(""),
    fecha_contrato: str = Form(""),
    usuario: dict = Depends(_rbac_editar),
):
    data = {
        "nombre": nombre, "tipo_producto": tipo_producto,
        "comision_pactada_pct": float(comision_pactada_pct) if comision_pactada_pct.strip() else None,
        "contacto": contacto or None,
        "fecha_contrato": fecha_contrato or None,
    }
    try:
        await actualizar_proveedor(usuario, proveedor_id, data)
    except ProveedorInvalido as exc:
        return redirect_con_mensaje("/backoffice/proveedores", str(exc), tipo="error")
    return redirect_con_mensaje("/backoffice/proveedores", "Proveedor actualizado")


@router.post("/{proveedor_id}/alternar-activo")
async def alternar_activo(proveedor_id: str, usuario: dict = Depends(_rbac_editar)):
    try:
        actualizado = await alternar_activo_proveedor(usuario, proveedor_id)
    except ProveedorInvalido as exc:
        return redirect_con_mensaje("/backoffice/proveedores", str(exc), tipo="error")
    mensaje = "Proveedor reactivado" if actualizado["activo"] else "Proveedor desactivado"
    return redirect_con_mensaje("/backoffice/proveedores", mensaje)
