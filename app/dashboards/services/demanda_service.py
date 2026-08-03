"""DB-06 — Demanda por Tipo de Producto.

`agg_ingresos_por_producto_mes`/`agg_conversion_busqueda_reserva`
(ClickHouse, mensual) para los KPIs y la tabla de métricas. Las 2
visualizaciones "por semana" (reservas por producto, tendencia 8 semanas)
no existen a esa granularidad en ClickHouse — se calculan en vivo sobre
`reserva_items`, mismo criterio que la tendencia diaria de DB-01.
"""

from __future__ import annotations

import datetime

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.clickhouse_client import query_dicts


async def obtener_datos_demanda(desde: datetime.date, hasta: datetime.date) -> dict:
    filas_ingresos = query_dicts(
        """
        SELECT tipo_producto, sum(total_reservas) AS total_reservas, sum(ingresos_brutos) AS ingresos_brutos
        FROM agg_ingresos_por_producto_mes
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY tipo_producto ORDER BY ingresos_brutos DESC
        """,
        {"desde": desde, "hasta": hasta},
    )
    filas_conversion = query_dicts(
        """
        SELECT tipo_producto, sum(total_busquedas) AS total_busquedas, sum(total_carritos) AS total_carritos,
               sum(total_confirmadas) AS total_confirmadas
        FROM agg_conversion_busqueda_reserva
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY tipo_producto
        """,
        {"desde": desde, "hasta": hasta},
    )
    conv_por_tipo = {f["tipo_producto"]: f for f in filas_conversion}

    metricas = []
    for f in filas_ingresos:
        c = conv_por_tipo.get(f["tipo_producto"], {"total_busquedas": 0, "total_carritos": 0, "total_confirmadas": 0})
        tasa_conv = round(c["total_confirmadas"] / c["total_busquedas"] * 100, 2) if c["total_busquedas"] else 0.0
        abandono = round((c["total_carritos"] - c["total_confirmadas"]) / c["total_carritos"] * 100, 2) if c["total_carritos"] else 0.0
        metricas.append({
            "tipo_producto": f["tipo_producto"], "total_reservas": f["total_reservas"],
            "ingresos_brutos": round(f["ingresos_brutos"], 2), "tasa_conversion": tasa_conv, "tasa_abandono": abandono,
        })

    producto_mas_vendido = max(metricas, key=lambda x: x["total_reservas"])["tipo_producto"] if metricas else None
    producto_mayor_ingreso = metricas[0]["tipo_producto"] if metricas else None  # ya viene ORDER BY ingresos_brutos DESC
    producto_mayor_conversion = max(metricas, key=lambda x: x["tasa_conversion"])["tipo_producto"] if metricas else None

    # ── Semanal en vivo — reservas por producto + tendencia 8 semanas ──
    reservas_repo = ReservasRepository()
    items = await reservas_repo.listar_todos_items()
    reservas = await reservas_repo.listar_todas()
    reserva_por_id = {r["id"]: r for r in reservas}

    hoy = datetime.date.today()
    inicio_8_semanas = hoy - datetime.timedelta(weeks=8)
    semana_tipo_conteo: dict[tuple[str, str], int] = {}
    for it in items:
        reserva = reserva_por_id.get(it.get("reserva_id"))
        if not reserva or not reserva.get("fecha_reserva"):
            continue
        fecha = datetime.datetime.fromisoformat(reserva["fecha_reserva"].replace("Z", "+00:00")).date()
        if fecha < inicio_8_semanas:
            continue
        if it["tipo_producto"] == "crucero" and (it.get("precio_final") or 0) > 50000:
            continue
        semana = (fecha - datetime.timedelta(days=fecha.weekday())).isoformat()
        clave = (semana, it["tipo_producto"])
        semana_tipo_conteo[clave] = semana_tipo_conteo.get(clave, 0) + 1

    semanas = sorted({k[0] for k in semana_tipo_conteo})
    tipos_top6 = [m["tipo_producto"] for m in sorted(metricas, key=lambda x: x["total_reservas"], reverse=True)[:6]]
    reservas_por_semana_producto = {
        tipo: [semana_tipo_conteo.get((s, tipo), 0) for s in semanas] for tipo in tipos_top6
    }

    return {
        "producto_mas_vendido": producto_mas_vendido,
        "producto_mayor_ingreso": producto_mayor_ingreso,
        "producto_mayor_conversion": producto_mayor_conversion,
        "ingresos_por_producto": filas_ingresos,
        "metricas_por_producto": metricas,
        "semanas": semanas,
        "reservas_por_semana_producto": reservas_por_semana_producto,
    }
