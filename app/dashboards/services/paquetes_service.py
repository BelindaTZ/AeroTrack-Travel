"""DB-07 — Paquetes y Carrito.

`agg_paquetes_margen_mes`/`agg_conversion_busqueda_reserva` (ClickHouse,
mensual) para los KPIs y las combinaciones. "Carritos creados vs
completados por día" necesita granularidad diaria que no existe en
ClickHouse — se aproxima en vivo: creados = carritos distintos con al
menos un ítem agregado ese día (`carrito_items.fecha_agregado`);
completados = reservas confirmadas ese día (no hay FK directo
carrito_id -> reserva_id en el modelo, así que se usa la reserva
confirmada como proxy de "carrito que llegó a buen puerto", mismo
criterio que la definición de "checkout" acordada en la Fase 1 de este
proyecto: el evento de negocio equivalente, no un ID literal)."""

from __future__ import annotations

import datetime

from app.carrito.repositories.carrito_repo import CarritoRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.clickhouse_client import query_dicts

BENCHMARK_ABANDONO_CARRITO = 93.96


async def obtener_datos_paquetes(desde: datetime.date, hasta: datetime.date) -> dict:
    filas_paquetes = query_dicts(
        """
        SELECT tipo_combinacion, sum(total_vendidos) AS total_vendidos, sum(ingresos_brutos) AS ingresos_brutos,
               sum(margen_bruto) AS margen_bruto, avg(margen_porcentaje) AS margen_porcentaje
        FROM agg_paquetes_margen_mes
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY tipo_combinacion ORDER BY total_vendidos DESC
        """,
        {"desde": desde, "hasta": hasta},
    )
    total_vendidos = sum(f["total_vendidos"] for f in filas_paquetes)
    margen_bruto_total = sum(f["margen_bruto"] for f in filas_paquetes)
    margen_promedio_por_paquete = round(margen_bruto_total / total_vendidos, 2) if total_vendidos else 0.0
    margen_pct_promedio = round(sum(f["margen_porcentaje"] for f in filas_paquetes) / len(filas_paquetes), 2) if filas_paquetes else 0.0

    filas_conversion = query_dicts(
        """
        SELECT sum(total_carritos) AS carritos, sum(total_confirmadas) AS confirmadas
        FROM agg_conversion_busqueda_reserva
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    conv = filas_conversion[0] if filas_conversion else {"carritos": 0, "confirmadas": 0}
    tasa_abandono = round((conv["carritos"] - conv["confirmadas"]) / conv["carritos"] * 100, 2) if conv["carritos"] else 0.0

    # ── Carritos creados vs completados por día (en vivo) ──────────────
    carrito_items = await CarritoRepository().listar_todos_items()
    reservas = await ReservasRepository().listar_todas()

    creados_por_dia: dict[str, set] = {}
    for it in carrito_items:
        if not it.get("fecha_agregado"):
            continue
        fecha = datetime.datetime.fromisoformat(it["fecha_agregado"].replace("Z", "+00:00")).date()
        if not (desde <= fecha <= hasta):
            continue
        creados_por_dia.setdefault(fecha.isoformat(), set()).add(it["carrito_id"])

    completados_por_dia: dict[str, int] = {}
    for r in reservas:
        if r.get("estado") != "confirmada" or not r.get("fecha_reserva"):
            continue
        fecha = datetime.datetime.fromisoformat(r["fecha_reserva"].replace("Z", "+00:00")).date()
        if not (desde <= fecha <= hasta):
            continue
        clave = fecha.isoformat()
        completados_por_dia[clave] = completados_por_dia.get(clave, 0) + 1

    dias = [(desde + datetime.timedelta(days=i)) for i in range((hasta - desde).days + 1)]
    carritos_por_dia = {
        "dias": [d.isoformat() for d in dias],
        "creados": [len(creados_por_dia.get(d.isoformat(), set())) for d in dias],
        "completados": [completados_por_dia.get(d.isoformat(), 0) for d in dias],
    }

    top_5 = filas_paquetes[:5]

    return {
        "total_vendidos": total_vendidos,
        "margen_promedio_por_paquete": margen_promedio_por_paquete,
        "margen_pct_promedio": margen_pct_promedio,
        "tasa_abandono_carrito": tasa_abandono,
        "benchmark_abandono": BENCHMARK_ABANDONO_CARRITO,
        "ventas_por_combinacion": filas_paquetes,
        "carritos_por_dia": carritos_por_dia,
        "top_5_combinaciones": top_5,
    }
