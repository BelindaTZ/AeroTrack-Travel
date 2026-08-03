"""CU-T16 (reporte de reservas por estado/período), CU-T17 (monitor de pago
próximo a vencer), CU-T43 (mis reservas asistidas por período — Agente) y
CU-T44 (cola de pago próximo a vencer en mi cartera — Agente).

WP-04 (auditoría de WorkPanels, 2026-07-31) — filtros ampliados (canal,
código, nombre de pasajero), paginación, y acciones por fila según estado
(ver `reportes_service.py`) en vez del simple link "Ver" de antes.
"""

from fastapi import APIRouter, Depends, Query, Request

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.services.reportes_service import listar_reservas_backoffice
from app.seguridad.services.rbac_service import requiere_permiso
from app.shared.csv_export import csv_response
from app.shared.descripcion_producto import describir_item
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/reservas")

ESTADOS = ["pendiente_pago", "confirmada", "modificada", "cancelada", "completada"]
CANALES = ["autoservicio", "asistida"]
TIPOS_PRODUCTO = ["vuelo", "hotel", "auto", "actividad", "crucero"]

COLUMNAS_EXPORTAR = [
    ("codigo_reserva", lambda r: r["codigo_reserva"]),
    ("pasajero", lambda r: r.get("pasajero_nombre", "")),
    ("estado", lambda r: r["estado"]),
    ("canal", lambda r: r["canal"]),
    ("total_pagar", lambda r: r.get("total_pagar", 0)),
    ("fecha_reserva", lambda r: r.get("fecha_reserva", "")),
    ("horas_para_vencer", lambda r: r["horas_para_vencer"] if r["horas_para_vencer"] is not None else ""),
]


def _filtrar_urgentes(filas: list[dict], urgentes_24h: str) -> list[dict]:
    if not urgentes_24h:
        return filas
    return [f for f in filas if f["horas_para_vencer"] is not None and f["horas_para_vencer"] < 24]


@router.get("/reporte")
async def reporte(
    request: Request,
    estado: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    canal: str = Query(""),
    codigo_reserva: str = Query(""),
    nombre_pasajero: str = Query(""),
    urgentes_24h: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("reservas", "ver")),
):
    """CU-T16/T17 — reporte general (Ventas): todas las reservas, filtrable
    por estado/período/canal/código/pasajero; cada fila muestra horas para
    vencer si aplica y las acciones válidas según su estado. IS-09
    (auditoría de informes simples, 2026-08-01) — `urgentes_24h` agrega el
    umbral explícito de "próximas a vencer" que antes solo se podía leer
    manualmente en la columna "Vence en"; al activarlo también ordena por
    urgencia (igual que ya hacía "mi cartera")."""
    filas = await listar_reservas_backoffice(
        estado=estado or None, desde=desde or None, hasta=hasta or None,
        canal=canal or None, codigo_reserva=codigo_reserva or None,
        nombre_pasajero=nombre_pasajero or None,
    )
    filas = _filtrar_urgentes(filas, urgentes_24h)
    if urgentes_24h:
        filas.sort(key=lambda r: r["horas_para_vencer"])
    pagina = paginar(filas, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "estados": ESTADOS,
            "canales": CANALES,
            "filtros": {
                "estado": estado, "desde": desde, "hasta": hasta, "canal": canal,
                "codigo_reserva": codigo_reserva, "nombre_pasajero": nombre_pasajero,
                "urgentes_24h": urgentes_24h,
            },
            "titulo": "Reporte de reservas",
            "cu_ref": "CU-T16/T17",
            "solo_mi_cartera": False,
            "volver_a": "/backoffice/reservas/reporte",
            "export_path": "/backoffice/reservas/reporte/exportar",
        }
    )
    return templates.TemplateResponse(request, "backoffice/reporte_reservas.html", contexto)


@router.get("/reporte/exportar")
async def exportar_reporte(
    estado: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    canal: str = Query(""),
    codigo_reserva: str = Query(""),
    nombre_pasajero: str = Query(""),
    urgentes_24h: str = Query(""),
    usuario: dict = Depends(requiere_permiso("reservas", "ver")),
):
    filas = await listar_reservas_backoffice(
        estado=estado or None, desde=desde or None, hasta=hasta or None,
        canal=canal or None, codigo_reserva=codigo_reserva or None,
        nombre_pasajero=nombre_pasajero or None,
    )
    filas = _filtrar_urgentes(filas, urgentes_24h)
    return csv_response(filas, COLUMNAS_EXPORTAR, "reporte_reservas.csv")


@router.get("/mi-cartera")
async def mi_cartera(
    request: Request,
    estado: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    canal: str = Query(""),
    codigo_reserva: str = Query(""),
    nombre_pasajero: str = Query(""),
    urgentes_24h: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("reservas", "ver")),
):
    """CU-T43/T44 — mi cartera (Agente): mismo reporte, recortado a las
    reservas asistidas por MÍ (`agente_id == usuario.id`), sin depender de
    que el Agente sepa filtrar por su propio id. IS-16 (auditoría de
    informes simples, 2026-08-01) — `urgentes_24h` es el mismo umbral
    explícito de IS-09; la vista ya ordenaba por urgencia, esto solo acota
    la lista a las que realmente vencen pronto."""
    filas = await listar_reservas_backoffice(
        estado=estado or None, desde=desde or None, hasta=hasta or None,
        canal=canal or None, codigo_reserva=codigo_reserva or None,
        nombre_pasajero=nombre_pasajero or None, agente_id=usuario["id"],
    )
    filas = _filtrar_urgentes(filas, urgentes_24h)
    filas.sort(key=lambda r: (r["horas_para_vencer"] is None, r["horas_para_vencer"]))
    pagina = paginar(filas, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "estados": ESTADOS,
            "canales": CANALES,
            "filtros": {
                "estado": estado, "desde": desde, "hasta": hasta, "canal": canal,
                "codigo_reserva": codigo_reserva, "nombre_pasajero": nombre_pasajero,
                "urgentes_24h": urgentes_24h,
            },
            "titulo": "Mi cartera de reservas asistidas",
            "cu_ref": "CU-T43/T44",
            "solo_mi_cartera": True,
            "volver_a": "/backoffice/reservas/mi-cartera",
            "export_path": "/backoffice/reservas/mi-cartera/exportar",
        }
    )
    return templates.TemplateResponse(request, "backoffice/reporte_reservas.html", contexto)


@router.get("/mi-cartera/exportar")
async def exportar_mi_cartera(
    estado: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    canal: str = Query(""),
    codigo_reserva: str = Query(""),
    nombre_pasajero: str = Query(""),
    urgentes_24h: str = Query(""),
    usuario: dict = Depends(requiere_permiso("reservas", "ver")),
):
    filas = await listar_reservas_backoffice(
        estado=estado or None, desde=desde or None, hasta=hasta or None,
        canal=canal or None, codigo_reserva=codigo_reserva or None,
        nombre_pasajero=nombre_pasajero or None, agente_id=usuario["id"],
    )
    filas = _filtrar_urgentes(filas, urgentes_24h)
    return csv_response(filas, COLUMNAS_EXPORTAR, "mi_cartera_reservas.csv")


async def _items_filtrados(tipo_producto: str, estado: str, desde: str, hasta: str) -> list[dict]:
    """IS-10 — enriquece cada `reserva_item` con el código y estado de su
    reserva padre (`estado de la reserva padre`, pedido explícitamente) y
    una descripción legible vía `describir_item` (compartida con Carrito/
    Mis reservas, evita resolver cada tipo_producto de nuevo acá)."""
    repo = ReservasRepository()
    items = await repo.listar_todos_items(tipo_producto=tipo_producto or None, desde=desde or None, hasta=hasta or None)

    reservas_cache: dict[str, dict | None] = {}
    items_out = []
    for item in items:
        reserva_id = item.get("reserva_id")
        if reserva_id not in reservas_cache:
            reservas_cache[reserva_id] = await repo.obtener_reserva(reserva_id) if reserva_id else None
        reserva = reservas_cache[reserva_id]
        if estado and (not reserva or reserva.get("estado") != estado):
            continue
        descripcion = await describir_item(item)
        items_out.append(
            {
                **item,
                "codigo_reserva": reserva["codigo_reserva"] if reserva else "—",
                "estado_reserva": reserva["estado"] if reserva else "—",
                "descripcion": descripcion["titulo"],
            }
        )
    return items_out


@router.get("/items")
async def listar_items(
    request: Request,
    tipo_producto: str = Query(""),
    estado: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    page: int = Query(1, ge=1),
    usuario: dict = Depends(requiere_permiso("reservas", "ver")),
):
    items_out = await _items_filtrados(tipo_producto, estado, desde, hasta)
    pagina = paginar(items_out, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "tipos_producto": TIPOS_PRODUCTO,
            "estados": ESTADOS,
            "filtros": {"tipo_producto": tipo_producto, "estado": estado, "desde": desde, "hasta": hasta},
        }
    )
    return templates.TemplateResponse(request, "backoffice/reporte_items.html", contexto)


@router.get("/items/exportar")
async def exportar_items(
    tipo_producto: str = Query(""),
    estado: str = Query(""),
    desde: str = Query(""),
    hasta: str = Query(""),
    usuario: dict = Depends(requiere_permiso("reservas", "ver")),
):
    items_out = await _items_filtrados(tipo_producto, estado, desde, hasta)
    return csv_response(
        items_out,
        [
            ("tipo_producto", lambda i: i["tipo_producto"]),
            ("codigo_reserva", lambda i: i["codigo_reserva"]),
            ("descripcion", lambda i: i["descripcion"]),
            ("precio_final", lambda i: i.get("precio_final", "")),
            ("fecha", lambda i: i.get("created", "")),
            ("estado_reserva", lambda i: i["estado_reserva"]),
        ],
        "items_reserva.csv",
    )
