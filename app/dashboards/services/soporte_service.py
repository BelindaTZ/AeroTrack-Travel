"""DB-09 — Calidad de Soporte y Atención.

`agg_satisfaccion_soporte` (ClickHouse, mensual, única fuente real para
este dashboard). "Satisfacción en el tiempo, por semana" se muestra por
MES en su lugar — no existe una fuente con calificación fechada a nivel
semanal en todo el proyecto (`articulo_calificaciones` no tiene fecha de
calificación en su esquema, solo `util` arriba/abajo). "Artículos más
consultados" reutiliza `metricas_satisfaccion()` del propio módulo
Centro de Ayuda, que ya documenta por qué "consultado" = calificado (no
hay contador de vistas en el esquema real)."""

from __future__ import annotations

import datetime

from app.centro_ayuda.services.centro_ayuda_service import metricas_satisfaccion
from app.shared.clickhouse_client import query_dicts


async def obtener_datos_soporte(desde: datetime.date, hasta: datetime.date) -> dict:
    filas_periodo = query_dicts(
        """
        SELECT avg(calificacion_promedio) AS calificacion, avg(tasa_escalacion) AS escalacion,
               avg(tiempo_promedio_resolucion_horas) AS tiempo_resolucion, sum(total_consultas) AS total_consultas
        FROM agg_satisfaccion_soporte
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    kpis = filas_periodo[0] if filas_periodo else {}

    filas_categoria = query_dicts(
        """
        SELECT categoria, avg(calificacion_promedio) AS calificacion, sum(total_consultas) AS total_consultas
        FROM agg_satisfaccion_soporte
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY categoria ORDER BY calificacion ASC
        """,
        {"desde": desde, "hasta": hasta},
    )

    hoy = datetime.date.today()
    inicio_6m = hoy.replace(day=1)
    for _ in range(5):
        inicio_6m = (inicio_6m - datetime.timedelta(days=1)).replace(day=1)
    tendencia_mensual = query_dicts(
        """
        SELECT periodo, avg(calificacion_promedio) AS calificacion
        FROM agg_satisfaccion_soporte
        WHERE periodo >= toStartOfMonth(toDate(%(inicio)s))
        GROUP BY periodo ORDER BY periodo
        """,
        {"inicio": inicio_6m},
    )

    articulos = (await metricas_satisfaccion(desde.isoformat()))["articulos"][:10]

    return {
        "calificacion_promedio": round(kpis.get("calificacion") or 0, 2),
        "tasa_escalacion": round(kpis.get("escalacion") or 0, 2),
        "tiempo_promedio_resolucion": round(kpis.get("tiempo_resolucion") or 0, 2),
        "por_categoria": filas_categoria,
        "tendencia_mensual": tendencia_mensual,
        "articulos_top": articulos,
    }
