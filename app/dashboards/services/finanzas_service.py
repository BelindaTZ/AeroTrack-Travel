"""DB-02 — Control Financiero del Período.

Igual que DB-01: ClickHouse (`agg_ingresos_por_producto_mes`, mensual) para
lo que la spec pide a ese nivel, y `FacturacionRepository`/`ReservasRepository`
en vivo para lo que necesita datos operacionales de hoy (comisiones/remesas
pendientes, mapa de calor diario).

Dos gaps de datos reales, no de código (mismo criterio que
`costo_componentes=0` documentado en `aerotrack_travel_etl_finanzas_tasks.py`):
- No existe ningún campo "fecha de vencimiento" en `remesas` — solo
  `fecha_generacion`. Se muestra la remesa pendiente más antigua como proxy
  de urgencia, sin inventar una fecha límite que no existe en el esquema.
- No hay ningún "take rate objetivo" configurable en el proyecto — se usa
  5% como referencia documentada (típico de la industria para vuelos), no
  configurable todavía.
"""

from __future__ import annotations

import datetime

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.clickhouse_client import query_dicts
from app.vuelos.repositories.catalogo_reader import CatalogoVuelosReader

TAKE_RATE_OBJETIVO = 5.0  # referencia de industria, no configurable — ver docstring


async def obtener_datos_finanzas(desde: datetime.date, hasta: datetime.date) -> dict:
    # ── ClickHouse (mensual) ──────────────────────────────────────────
    filas_periodo = query_dicts(
        """
        SELECT tipo_producto, sum(total_reservas) AS total_reservas, sum(ingresos_brutos) AS ingresos_brutos,
               sum(comisiones) AS comisiones, sum(reembolsos) AS reembolsos, sum(ingresos_netos) AS ingresos_netos
        FROM agg_ingresos_por_producto_mes
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY tipo_producto ORDER BY ingresos_netos DESC
        """,
        {"desde": desde, "hasta": hasta},
    )
    ingresos_totales = sum(f["ingresos_netos"] for f in filas_periodo)
    ingresos_brutos_totales = sum(f["ingresos_brutos"] for f in filas_periodo)
    comisiones_totales = sum(f["comisiones"] for f in filas_periodo)
    reembolsos_totales = sum(f["reembolsos"] for f in filas_periodo)
    total_reservas = sum(f["total_reservas"] for f in filas_periodo)
    take_rate = round(comisiones_totales / ingresos_brutos_totales * 100, 2) if ingresos_brutos_totales else 0.0
    ingreso_promedio = round(ingresos_brutos_totales / total_reservas, 2) if total_reservas else 0.0

    hoy = datetime.date.today()
    inicio_6m = (hoy.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    for _ in range(5):
        inicio_6m = (inicio_6m.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    tendencia = query_dicts(
        """
        SELECT periodo, sum(ingresos_netos) AS ingresos_netos
        FROM agg_ingresos_por_producto_mes
        WHERE periodo >= toStartOfMonth(toDate(%(inicio)s))
        GROUP BY periodo ORDER BY periodo
        """,
        {"inicio": inicio_6m},
    )

    # ── Operacional en vivo ────────────────────────────────────────────
    fact = FacturacionRepository()
    comisiones_pendientes = await fact.listar_comisiones(filtro_campos={"estado": "pendiente_cobro"})
    remesas_pendientes = await fact.listar_remesas(estado="pendiente")

    aerolineas = await CatalogoVuelosReader().listar_aerolineas_activas()
    nombre_por_id = {a["id"]: a["nombre"] for a in aerolineas}

    monto_por_aerolinea: dict[str, float] = {}
    for c in comisiones_pendientes:
        nombre = nombre_por_id.get(c.get("aerolinea_id"), "Aerolínea desconocida")
        monto_por_aerolinea[nombre] = monto_por_aerolinea.get(nombre, 0) + (c.get("monto") or 0)
    lista_aerolineas_comisiones = sorted(
        [{"aerolinea": k, "monto": round(v, 2)} for k, v in monto_por_aerolinea.items()],
        key=lambda x: x["monto"], reverse=True,
    )

    remesa_mas_antigua = min(
        (r["fecha_generacion"] for r in remesas_pendientes if r.get("fecha_generacion")), default=None
    )

    # Reembolsos y remesas del período (para la tarjeta doble y el gráfico
    # ingresos-vs-reembolsos) — remesas se atribuyen 100% a "vuelo" (mismo
    # criterio que comisiones en el ETL: solo vuelos generan remesa a
    # aerolínea en este proyecto).
    reservas_repo = ReservasRepository()
    reembolsos_periodo = [
        r for r in await fact.listar_reembolsos(desde=desde.isoformat(), hasta=hasta.isoformat())
    ]
    monto_reembolsos_periodo = round(sum(r.get("monto") or 0 for r in reembolsos_periodo), 2)

    remesas_periodo = await fact.listar_remesas(desde=desde.isoformat(), hasta=hasta.isoformat())
    monto_remesas_periodo = round(sum(r.get("monto_total") or 0 for r in remesas_periodo), 2)

    desglose = []
    for f in filas_periodo:
        desglose.append({
            "tipo_producto": f["tipo_producto"],
            "ingresos": round(f["ingresos_brutos"], 2),
            "comisiones": round(f["comisiones"], 2),
            "reembolsos": round(f["reembolsos"], 2),
            "remesas": monto_remesas_periodo if f["tipo_producto"] == "vuelo" else 0.0,
        })

    # ── Mapa de calor — ingresos por día del mes (vivo, granularidad diaria) ──
    # Una cuadrícula 5×7 solo tiene sentido para UN mes calendario — se usa
    # el mes de `hasta` (fin del período elegido), no todo el rango [desde,
    # hasta]: sumar "día 27" de 6 meses distintos en la misma celda no
    # tendría lectura real.
    mes_heatmap = hasta.replace(day=1)
    items = await reservas_repo.listar_todos_items()
    reservas = await reservas_repo.listar_todas()
    reserva_por_id = {r["id"]: r for r in reservas}
    ingresos_por_dia: dict[int, float] = {}
    for it in items:
        reserva = reserva_por_id.get(it.get("reserva_id"))
        if not reserva or not reserva.get("fecha_reserva"):
            continue
        fecha = datetime.datetime.fromisoformat(reserva["fecha_reserva"].replace("Z", "+00:00")).date()
        if fecha.year != mes_heatmap.year or fecha.month != mes_heatmap.month:
            continue
        if it["tipo_producto"] == "crucero" and (it.get("precio_final") or 0) > 50000:
            continue  # mismo outlier que DB-01, ver comercial_service.py
        monto = (it.get("precio_final") or 0) * (it.get("cantidad") or 1)
        ingresos_por_dia[fecha.day] = ingresos_por_dia.get(fecha.day, 0) + monto
    mapa_calor = [{"dia": d, "monto": round(m, 2)} for d, m in sorted(ingresos_por_dia.items())]

    return {
        "ingresos_totales": round(ingresos_totales, 2),
        "take_rate": take_rate,
        "take_rate_objetivo": TAKE_RATE_OBJETIVO,
        "ingreso_promedio": ingreso_promedio,
        "comisiones_pendientes_total": round(sum(c.get("monto") or 0 for c in comisiones_pendientes), 2),
        "comisiones_pendientes_por_aerolinea": lista_aerolineas_comisiones,
        "remesas_pendientes_total": round(sum(r.get("monto_total") or 0 for r in remesas_pendientes), 2),
        "remesas_pendientes_conteo": len(remesas_pendientes),
        "remesa_mas_antigua": remesa_mas_antigua,
        "reembolsos_periodo": monto_reembolsos_periodo,
        "reembolsos_pct_ingresos": round(monto_reembolsos_periodo / ingresos_brutos_totales * 100, 2) if ingresos_brutos_totales else 0.0,
        "tendencia_6_periodos": tendencia,
        "desglose": desglose,
        "mapa_calor": mapa_calor,
    }
