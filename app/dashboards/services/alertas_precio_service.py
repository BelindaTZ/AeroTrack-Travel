"""DB-12 — Alertas de Precio y Conversión.

`agg_alertas_conversion` (ClickHouse, mensual, sin desglose por ruta) para
tasa de conversión/tiempo promedio. "Alertas por ruta" y "rutas con alerta
pero sin conversión" necesitan desglose por origen-destino que no existe
en ClickHouse — se calculan en vivo, mismo criterio de matching que usa
`aerotrack_travel_etl_clientes_tasks.py` (alerta convierte si el mismo
pasajero reserva esa ruta después de crear la alerta). "Conversiones por
semana" se muestra por MES — la tabla ClickHouse no tiene semana."""

from __future__ import annotations

import datetime

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.clickhouse_client import query_dicts


async def obtener_datos_alertas_precio(desde: datetime.date, hasta: datetime.date) -> dict:
    reservas_repo = ReservasRepository()
    alertas = await reservas_repo.listar_todas_alertas()
    alertas_activas = [a for a in alertas if a.get("activa")]

    por_ruta: dict[str, int] = {}
    for a in alertas_activas:
        ruta = f"{a.get('origen_codigo', '?')}-{a.get('destino_codigo', '?')}"
        por_ruta[ruta] = por_ruta.get(ruta, 0) + 1
    top_10_rutas = sorted(
        [{"ruta": k, "alertas": v} for k, v in por_ruta.items()], key=lambda x: x["alertas"], reverse=True
    )[:10]

    filas_periodo = query_dicts(
        """
        SELECT sum(total_alertas_activas) AS activas, sum(total_conversiones) AS conversiones,
               avg(tiempo_promedio_conversion_horas) AS tiempo_promedio
        FROM agg_alertas_conversion
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    kpis = filas_periodo[0] if filas_periodo else {"activas": 0, "conversiones": 0, "tiempo_promedio": 0}
    tasa_conversion = round(kpis["conversiones"] / kpis["activas"] * 100, 2) if kpis["activas"] else 0.0

    hoy = datetime.date.today()
    inicio_6m = hoy.replace(day=1)
    for _ in range(5):
        inicio_6m = (inicio_6m - datetime.timedelta(days=1)).replace(day=1)
    tendencia_mensual = query_dicts(
        """
        SELECT periodo, sum(total_conversiones) AS conversiones
        FROM agg_alertas_conversion
        WHERE periodo >= toStartOfMonth(toDate(%(inicio)s))
        GROUP BY periodo ORDER BY periodo
        """,
        {"inicio": inicio_6m},
    )

    # ── Rutas con alerta pero sin conversión (en vivo) ─────────────────
    reservas = await reservas_repo.listar_todas()

    rutas_sin_conversion = []
    for a in alertas_activas:
        candidatas = [
            r for r in reservas
            if r.get("pasajero_titular_id") == a.get("pasajero_id")
            and r.get("fecha_reserva", "") > a.get("created", "")
        ]
        if not candidatas:
            rutas_sin_conversion.append({"ruta": f"{a.get('origen_codigo', '?')}-{a.get('destino_codigo', '?')}", "pasajero_id": a.get("pasajero_id")})

    return {
        "alertas_activas_total": len(alertas_activas),
        "tasa_conversion": tasa_conversion,
        "tiempo_promedio_horas": round(kpis["tiempo_promedio"] or 0, 2),
        "top_10_rutas": top_10_rutas,
        "tendencia_mensual": tendencia_mensual,
        "rutas_sin_conversion": rutas_sin_conversion[:15],
    }
