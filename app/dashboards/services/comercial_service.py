"""DB-01 — Rendimiento Comercial y Embudo de Conversión.

Mezcla dos fuentes a propósito, no por descuido:
- `agg_ingresos_por_producto_mes` / `agg_conversion_busqueda_reserva`
  (ClickHouse, granularidad MENSUAL) para los KPIs de conversión/ingresos
  que la spec define a ese nivel.
- `ReservasRepository` (MinIO operacional en vivo, directo — la app SÍ
  puede leer operacional, la regla de "nunca directo" es solo para los
  DAGs, ver `app/shared/router_interno_analitica.py`) para todo lo que la
  spec pide con granularidad DIARIA (tendencia de reservas por día, canal,
  top productos, alerta <24h) — no existe una tabla ClickHouse a nivel de
  día para esto, y la spec de DB-01 ya contempla explícitamente consultar
  MinIO directo para la alerta de expiración.
"""

from __future__ import annotations

import datetime

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.clickhouse_client import query_dicts

_BENCHMARK_ABANDONO_CARRITO = 93.96  # OTA industry, spec DB-01/DB-07


def _rango_anterior(desde: datetime.date, hasta: datetime.date) -> tuple[datetime.date, datetime.date]:
    duracion = (hasta - desde).days + 1
    return desde - datetime.timedelta(days=duracion), desde - datetime.timedelta(days=1)


def _parse(fecha_str: str) -> datetime.date:
    return datetime.datetime.fromisoformat(fecha_str.replace("Z", "+00:00")).date()


async def obtener_datos_comercial(desde: datetime.date, hasta: datetime.date) -> dict:
    # ── ClickHouse (mensual) — Grupo A conversión/ASV + Grupo B ingresos por producto
    filas_conversion = query_dicts(
        """
        SELECT sum(total_busquedas) AS busquedas, sum(total_carritos) AS carritos,
               sum(total_confirmadas) AS confirmadas
        FROM agg_conversion_busqueda_reserva
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    conv = filas_conversion[0] if filas_conversion else {"busquedas": 0, "carritos": 0, "confirmadas": 0}
    tasa_conversion = round(conv["confirmadas"] / conv["busquedas"] * 100, 2) if conv["busquedas"] else 0.0
    tasa_abandono = round((conv["carritos"] - conv["confirmadas"]) / conv["carritos"] * 100, 2) if conv["carritos"] else 0.0

    filas_ingresos = query_dicts(
        """
        SELECT tipo_producto, sum(total_reservas) AS total_reservas, sum(ingresos_brutos) AS ingresos_brutos
        FROM agg_ingresos_por_producto_mes
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY tipo_producto ORDER BY ingresos_brutos DESC
        """,
        {"desde": desde, "hasta": hasta},
    )
    total_reservas_ch = sum(f["total_reservas"] for f in filas_ingresos)
    total_ingresos_ch = sum(f["ingresos_brutos"] for f in filas_ingresos)
    asv = round(total_ingresos_ch / total_reservas_ch, 2) if total_reservas_ch else 0.0

    # ── Operacional en vivo (diario) ──────────────────────────────────
    repo = ReservasRepository()
    reservas = await repo.listar_todas()
    items = await repo.listar_todos_items()

    desde_ant, hasta_ant = _rango_anterior(desde, hasta)

    def _en_rango(r: dict, d: datetime.date, h: datetime.date) -> bool:
        f = _parse(r["fecha_reserva"])
        return d <= f <= h

    reservas_periodo = [r for r in reservas if _en_rango(r, desde, hasta)]
    reservas_periodo_anterior = [r for r in reservas if _en_rango(r, desde_ant, hasta_ant)]

    def _conteo_por_dia(lista: list[dict]) -> dict[str, int]:
        conteo: dict[str, int] = {}
        for r in lista:
            dia = r["fecha_reserva"][:10]
            conteo[dia] = conteo.get(dia, 0) + 1
        return conteo

    conteo_actual = _conteo_por_dia(reservas_periodo)
    conteo_anterior = _conteo_por_dia(reservas_periodo_anterior)
    dias_periodo = [(desde + datetime.timedelta(days=i)) for i in range((hasta - desde).days + 1)]
    dias_anterior = [(desde_ant + datetime.timedelta(days=i)) for i in range((hasta_ant - desde_ant).days + 1)]
    tendencia_reservas = {
        "dias": [d.isoformat() for d in dias_periodo],
        "actual": [conteo_actual.get(d.isoformat(), 0) for d in dias_periodo],
        "anterior": [conteo_anterior.get(a.isoformat(), 0) for a in dias_anterior[: len(dias_periodo)]],
    }

    canal_conteo: dict[str, int] = {}
    for r in reservas_periodo:
        if r["estado"] == "confirmada":
            canal_conteo[r["canal"]] = canal_conteo.get(r["canal"], 0) + 1

    reserva_ids_periodo = {r["id"] for r in reservas_periodo}
    items_periodo = [
        it for it in items
        if it["reserva_id"] in reserva_ids_periodo
        # mismo outlier de precio de cruceros que el ETL (Cruise Pricing API,
        # ver aerotrack_travel_etl_comercial_tasks.py) — esta ruta no pasa
        # por ClickHouse, así que el filtro hay que repetirlo acá.
        and not (it["tipo_producto"] == "crucero" and (it.get("precio_final") or 0) > 50000)
    ]
    top_productos: dict[str, dict] = {}
    for it in items_periodo:
        tp = it["tipo_producto"]
        acc = top_productos.setdefault(tp, {"tipo_producto": tp, "conteo": 0, "ingresos": 0.0})
        acc["conteo"] += 1
        acc["ingresos"] += (it.get("precio_final") or 0) * (it.get("cantidad") or 1)
    top_5 = sorted(top_productos.values(), key=lambda x: x["ingresos"], reverse=True)[:5]
    for p in top_5:
        p["ingresos"] = round(p["ingresos"], 2)

    ahora = datetime.datetime.now(datetime.UTC)
    limite_24h = ahora + datetime.timedelta(hours=24)
    proximas_a_expirar = [
        r for r in reservas
        if r["estado"] == "pendiente_pago"
        and r.get("fecha_expiracion_pago")
        and ahora <= datetime.datetime.fromisoformat(r["fecha_expiracion_pago"].replace("Z", "+00:00")) <= limite_24h
    ]

    return {
        "tasa_conversion": tasa_conversion,
        "asv": asv,
        "tasa_abandono": tasa_abandono,
        "benchmark_abandono": _BENCHMARK_ABANDONO_CARRITO,
        "ingresos_por_producto": filas_ingresos,
        "tendencia_reservas": tendencia_reservas,
        "canal": [{"canal": k, "total": v} for k, v in canal_conteo.items()],
        "top_productos": top_5,
        "reservas_por_expirar": len(proximas_a_expirar),
    }
