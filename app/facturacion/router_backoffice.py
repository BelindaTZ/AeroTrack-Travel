"""RF-FAC-004,005 (CU-O35,O36) — conciliación de comisiones y remesas."""

import datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.facturacion.services.comision_service import (
    ComisionNoEncontrada,
    ComisionYaCobrada,
    marcar_cobrada,
)
from app.facturacion.services.pago_service import (
    PagoNoAutorizado,
    PagoNoEncontrado,
    PagoRechazadoPorStripe,
    capturar_pago_diferido,
)
from app.facturacion.services.remesa_service import (
    RemesaInvalida,
    SinComisionesParaRemesa,
    generar_remesa,
    marcar_remesa_pagada,
)
from app.facturacion.services.reportes_service import (
    listar_facturas_backoffice,
    listar_pagos_backoffice,
    listar_reembolsos_backoffice,
)
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.csv_export import csv_response
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates
from app.vuelos.repositories.vuelos_repo import VuelosRepository

router = APIRouter(prefix="/backoffice")


def _resumen_por_aerolinea(comisiones_pendientes: list[dict], nombre_por_id: dict[str, str]) -> list[dict]:
    """IS-20 (auditoría de informes simples, sesión 2026-08-01) — agrupa las
    comisiones `pendiente_cobro` por aerolínea para el informe de cobranza;
    la lista detalle de abajo (por comisión individual) se conserva intacta
    para no romper la acción operativa "marcar cobrada"."""
    hoy = datetime.datetime.now(datetime.UTC).date()
    grupos: dict[str, list[dict]] = {}
    for c in comisiones_pendientes:
        grupos.setdefault(c["aerolinea_id"], []).append(c)

    resumen = []
    for aerolinea_id, filas in grupos.items():
        fecha_devengo = min(f.get("created") or "" for f in filas)
        try:
            fecha_devengo_dt = datetime.datetime.strptime(fecha_devengo[:10], "%Y-%m-%d").date()
            dias_transcurridos = (hoy - fecha_devengo_dt).days
        except ValueError:
            dias_transcurridos = 0
        resumen.append(
            {
                "aerolinea_id": aerolinea_id,
                "aerolinea_nombre": nombre_por_id.get(aerolinea_id, ""),
                "numero_reservas": len({f["reserva_id"] for f in filas}),
                "fecha_devengo": fecha_devengo[:10] if fecha_devengo else "",
                "monto_acumulado": sum(f.get("monto", 0) for f in filas),
                "dias_transcurridos": dias_transcurridos,
                "estado": "pendiente_cobro",
            }
        )
    resumen.sort(key=lambda r: r["monto_acumulado"], reverse=True)
    return resumen


async def _comisiones_filtradas(estado: str | None, aerolinea_id: str | None, desde: str | None, hasta: str | None):
    repo = FacturacionRepository()
    vuelos_repo = VuelosRepository()

    filtro_campos = {}
    if estado:
        filtro_campos["estado"] = estado
    if aerolinea_id:
        filtro_campos["aerolinea_id"] = aerolinea_id

    comisiones = await repo.listar_comisiones(filtro_campos or None, desde=desde or None, hasta=hasta or None)
    aerolineas = await vuelos_repo.listar_aerolineas_activas()
    nombre_por_id = {a["id"]: a["nombre"] for a in aerolineas}
    comisiones_out = [{**c, "aerolinea_nombre": nombre_por_id.get(c["aerolinea_id"], "")} for c in comisiones]
    return comisiones_out, aerolineas, nombre_por_id


@router.get("/comisiones")
async def listar_comisiones(
    request: Request,
    estado: str | None = None,
    aerolinea_id: str | None = None,
    desde: str = Query(""),
    hasta: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "comisiones")),
):
    comisiones_out, aerolineas, nombre_por_id = await _comisiones_filtradas(estado, aerolinea_id, desde, hasta)
    pendientes = [c for c in comisiones_out if c["estado"] == "pendiente_cobro"]
    resumen = _resumen_por_aerolinea(pendientes, nombre_por_id)
    pagina = paginar(comisiones_out, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "resumen": resumen,
            "aerolineas": aerolineas,
            "filtros": {
                "estado": estado or "", "aerolinea_id": aerolinea_id or "",
                "desde": desde, "hasta": hasta,
            },
        }
    )
    return templates.TemplateResponse(request, "backoffice/comisiones.html", contexto)


@router.get("/comisiones/exportar")
async def exportar_comisiones(
    desde: str = Query(""),
    hasta: str = Query(""),
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "comisiones")),
):
    """IS-20 — exporta el resumen por aerolínea (no el detalle por
    comisión), que es la forma en la que se presenta este informe."""
    comisiones_out, _aerolineas, nombre_por_id = await _comisiones_filtradas(None, None, desde, hasta)
    pendientes = [c for c in comisiones_out if c["estado"] == "pendiente_cobro"]
    resumen = _resumen_por_aerolinea(pendientes, nombre_por_id)
    return csv_response(
        resumen,
        [
            ("aerolinea", lambda r: r["aerolinea_nombre"]),
            ("numero_reservas", lambda r: r["numero_reservas"]),
            ("fecha_devengo", lambda r: r["fecha_devengo"]),
            ("monto_acumulado", lambda r: f"{r['monto_acumulado']:.2f}"),
            ("dias_transcurridos", lambda r: r["dias_transcurridos"]),
            ("estado", lambda r: r["estado"]),
        ],
        "comisiones_pendientes_por_aerolinea.csv",
    )


@router.post("/comisiones/{comision_id}/marcar-cobrada")
async def marcar_cobrada_endpoint(
    comision_id: str,
    usuario: dict = Depends(requiere_permiso("facturacion", "editar", "comisiones")),
):
    try:
        await marcar_cobrada(comision_id)
    except ComisionNoEncontrada:
        return redirect_con_mensaje("/backoffice/comisiones", "Comisión no encontrada", tipo="error")
    except ComisionYaCobrada:
        return redirect_con_mensaje("/backoffice/comisiones", "Esa comisión ya estaba cobrada", tipo="error")

    await AuditService().insertar(
        "marcar_cobrada", "comisiones", usuario_id=usuario["id"], registro_id=comision_id
    )
    return redirect_con_mensaje("/backoffice/comisiones", "Comisión marcada como cobrada")


async def _remesas_filtradas(estado: str, aerolinea_id: str, desde: str, hasta: str):
    repo = FacturacionRepository()
    vuelos_repo = VuelosRepository()

    remesas = await repo.listar_remesas(
        estado=estado or None, aerolinea_id=aerolinea_id or None, desde=desde or None, hasta=hasta or None
    )
    aerolineas = await vuelos_repo.listar_aerolineas_activas()
    nombre_por_id = {a["id"]: a["nombre"] for a in aerolineas}
    remesas_out = [{**r, "aerolinea_nombre": nombre_por_id.get(r["aerolinea_id"], "")} for r in remesas]
    return remesas_out, aerolineas


@router.get("/remesas")
async def listar_remesas(
    request: Request,
    estado: str = Query(""),
    aerolinea_id: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "remesas")),
):
    remesas_out, aerolineas = await _remesas_filtradas(estado, aerolinea_id, desde, hasta)
    pagina = paginar(remesas_out, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "aerolineas": aerolineas,
            "filtros": {"estado": estado, "aerolinea_id": aerolinea_id, "desde": desde, "hasta": hasta},
        }
    )
    return templates.TemplateResponse(request, "backoffice/remesas.html", contexto)


@router.get("/remesas/exportar")
async def exportar_remesas(
    estado: str = Query(""),
    aerolinea_id: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "remesas")),
):
    remesas_out, _aerolineas = await _remesas_filtradas(estado, aerolinea_id, desde, hasta)
    return csv_response(
        remesas_out,
        [
            ("fecha_generacion", lambda r: r.get("fecha_generacion", "")),
            ("aerolinea", lambda r: r["aerolinea_nombre"]),
            ("periodo", lambda r: r.get("periodo", "")),
            ("monto_total", lambda r: r.get("monto_total", 0)),
            ("estado", lambda r: r["estado"]),
        ],
        "remesas.csv",
    )


@router.post("/remesas")
async def crear_remesa_endpoint(
    aerolinea_id: str = Form(...),
    periodo: str = Form(...),
    usuario: dict = Depends(requiere_permiso("facturacion", "crear", "remesas")),
):
    try:
        remesa = await generar_remesa(aerolinea_id, periodo)
    except SinComisionesParaRemesa:
        return redirect_con_mensaje(
            "/backoffice/remesas", "No hay comisiones cobradas sin remesar para esa aerolínea", tipo="error"
        )

    await AuditService().insertar(
        "generar_remesa",
        "remesas",
        usuario_id=usuario["id"],
        registro_id=remesa["id"],
        detalle={"aerolinea_id": aerolinea_id, "periodo": periodo, "monto_total": remesa["monto_total"]},
    )
    return redirect_con_mensaje("/backoffice/remesas", "Remesa generada")


@router.post("/remesas/{remesa_id}/marcar-pagada")
async def marcar_remesa_pagada_endpoint(
    remesa_id: str,
    usuario: dict = Depends(requiere_permiso("facturacion", "editar", "remesas")),
):
    try:
        await marcar_remesa_pagada(usuario, remesa_id)
    except RemesaInvalida as exc:
        return redirect_con_mensaje("/backoffice/remesas", str(exc), tipo="error")
    return redirect_con_mensaje("/backoffice/remesas", "Remesa marcada como pagada")


@router.get("/pagos-diferidos")
async def listar_pagos_diferidos(
    request: Request,
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "pagos")),
):
    """RF-FAC-012 (CU-O86) — pagos `autorizado` esperando que el hotel
    confirme la disponibilidad para completar la captura."""
    facturacion_repo = FacturacionRepository()
    reservas_repo = ReservasRepository()

    pagos = await facturacion_repo.pagos_por_estado("autorizado")
    pagos_out = []
    for pago in pagos:
        reserva = await reservas_repo.obtener_reserva(pago["reserva_id"])
        pagos_out.append({"pago": pago, "codigo_reserva": reserva["codigo_reserva"] if reserva else "?"})

    contexto = await nav_context(usuario)
    contexto.update({"pagos": pagos_out})
    return templates.TemplateResponse(request, "backoffice/pagos_diferidos.html", contexto)


@router.post("/pagos-diferidos/{pago_id}/capturar")
async def capturar_pago_diferido_endpoint(
    pago_id: str,
    usuario: dict = Depends(requiere_permiso("facturacion", "editar", "pagos")),
):
    try:
        await capturar_pago_diferido(pago_id)
    except PagoNoEncontrado:
        return RedirectResponse("/backoffice/pagos-diferidos?mensaje=Pago no encontrado", status_code=303)
    except PagoNoAutorizado:
        return RedirectResponse(
            "/backoffice/pagos-diferidos?mensaje=Ese pago ya no está pendiente de captura", status_code=303
        )
    except PagoRechazadoPorStripe as exc:
        return RedirectResponse(
            f"/backoffice/pagos-diferidos?mensaje=Captura rechazada: {exc.motivo}", status_code=303
        )

    await AuditService().insertar(
        "capturar_pago_diferido", "pagos", usuario_id=usuario["id"], registro_id=pago_id
    )
    return RedirectResponse("/backoffice/pagos-diferidos?mensaje=Pago capturado", status_code=303)


@router.get("/politicas-reembolso")
async def listar_politicas_reembolso(
    request: Request,
    nombre: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("facturacion", "ver")),
):
    repo = FacturacionRepository()
    politicas = await repo.listar_politicas_reembolso(nombre=nombre or None)
    pagina = paginar(politicas, page)

    contexto = await nav_context(usuario)
    contexto.update({"pagina": pagina, "filtros": {"nombre": nombre}})
    return templates.TemplateResponse(request, "backoffice/politicas_reembolso.html", contexto)


@router.post("/politicas-reembolso/{politica_id}")
async def actualizar_politica_reembolso_endpoint(
    politica_id: str,
    nombre: str = Form(...),
    condiciones: str = Form(...),
    porcentaje_reembolso: float = Form(...),
    ventana_horas: float = Form(...),
    usuario: dict = Depends(requiere_permiso("facturacion", "editar")),
):
    repo = FacturacionRepository()
    await repo.actualizar_politica_reembolso(
        politica_id,
        {
            "nombre": nombre,
            "condiciones": condiciones,
            "porcentaje_reembolso": porcentaje_reembolso,
            "ventana_horas": ventana_horas,
        },
    )
    await AuditService().insertar(
        "actualizar_politica_reembolso", "politicas_reembolso", usuario_id=usuario["id"], registro_id=politica_id
    )
    return redirect_con_mensaje("/backoffice/politicas-reembolso", "Política actualizada")


@router.post("/politicas-reembolso")
async def crear_politica_reembolso_endpoint(
    nombre: str = Form(...),
    condiciones: str = Form(...),
    porcentaje_reembolso: float = Form(...),
    ventana_horas: float = Form(...),
    usuario: dict = Depends(requiere_permiso("facturacion", "crear")),
):
    repo = FacturacionRepository()
    politica = await repo.crear_politica_reembolso(
        {
            "nombre": nombre,
            "condiciones": condiciones,
            "porcentaje_reembolso": porcentaje_reembolso,
            "ventana_horas": ventana_horas,
        }
    )
    await AuditService().insertar(
        "crear_politica_reembolso", "politicas_reembolso", usuario_id=usuario["id"], registro_id=politica["id"]
    )
    return redirect_con_mensaje("/backoffice/politicas-reembolso", "Política creada")


# ── WP-15 (auditoría de WorkPanels, 2026-08-01) — Pagos y Facturas, solo
# lectura (sin acciones de escritura, según lo definido en priorización) ──

@router.get("/pagos")
async def listar_pagos(
    request: Request,
    estado: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    codigo_reserva: str = Query(""),
    nombre_pasajero: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "pagos")),
):
    pagos = await listar_pagos_backoffice(
        estado=estado, desde=desde, hasta=hasta, codigo_reserva=codigo_reserva, nombre_pasajero=nombre_pasajero
    )
    pagina = paginar(pagos, page)
    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "filtros": {
                "estado": estado, "desde": desde, "hasta": hasta,
                "codigo_reserva": codigo_reserva, "nombre_pasajero": nombre_pasajero,
            },
        }
    )
    return templates.TemplateResponse(request, "backoffice/pagos.html", contexto)


@router.get("/facturas")
async def listar_facturas(
    request: Request,
    desde: str = Query(""),
    hasta: str = Query(""),
    codigo_reserva: str = Query(""),
    nombre_pasajero: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "facturas")),
):
    facturas = await listar_facturas_backoffice(
        desde=desde, hasta=hasta, codigo_reserva=codigo_reserva, nombre_pasajero=nombre_pasajero
    )
    pagina = paginar(facturas, page)
    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "filtros": {"desde": desde, "hasta": hasta, "codigo_reserva": codigo_reserva, "nombre_pasajero": nombre_pasajero},
        }
    )
    return templates.TemplateResponse(request, "backoffice/facturas.html", contexto)


# ── IS-24 (auditoría de informes simples, 2026-08-01) — reembolsos por
# período; colección real `reembolsos` (dedicada), no `pagos.tipo="reembolso"`
# como sugería el encargo original — confirmado en la auditoría del catálogo
# de informes simples antes de implementar. ──────────────────────────────

ESTADOS_REEMBOLSO = ["procesado", "rechazado"]
TIPOS_PRODUCTO_REEMBOLSO = ["vuelo", "hotel", "auto", "actividad", "crucero"]


@router.get("/reembolsos")
async def listar_reembolsos(
    request: Request,
    estado: str = Query(""),
    motivo: str = Query(""),
    tipo_producto: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "reembolsos")),
):
    reembolsos = await listar_reembolsos_backoffice(
        estado=estado, motivo=motivo, desde=desde, hasta=hasta, tipo_producto=tipo_producto
    )
    pagina = paginar(reembolsos, page)
    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "estados": ESTADOS_REEMBOLSO,
            "tipos_producto": TIPOS_PRODUCTO_REEMBOLSO,
            "filtros": {
                "estado": estado, "motivo": motivo, "tipo_producto": tipo_producto, "desde": desde, "hasta": hasta,
            },
        }
    )
    return templates.TemplateResponse(request, "backoffice/reembolsos.html", contexto)


@router.get("/reembolsos/exportar")
async def exportar_reembolsos(
    estado: str = Query(""),
    motivo: str = Query(""),
    tipo_producto: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    usuario: dict = Depends(requiere_permiso("facturacion", "ver", "reembolsos")),
):
    reembolsos = await listar_reembolsos_backoffice(
        estado=estado, motivo=motivo, desde=desde, hasta=hasta, tipo_producto=tipo_producto
    )
    return csv_response(
        reembolsos,
        [
            ("fecha_solicitud", lambda r: r.get("fecha_solicitud", "")),
            ("codigo_reserva", lambda r: r["codigo_reserva"]),
            ("pasajero", lambda r: r["pasajero_nombre"]),
            ("motivo", lambda r: r.get("motivo", "")),
            ("monto", lambda r: r.get("monto", 0)),
            ("estado", lambda r: r["estado"]),
        ],
        "reembolsos.csv",
    )
