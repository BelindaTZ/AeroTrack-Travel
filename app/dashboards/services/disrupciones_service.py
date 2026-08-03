"""DB-03 — Monitoreo de Disrupciones.

`agg_disrupciones_aerolinea_ruta`/`agg_otp_aerolinea_mes` (ClickHouse) para
efectividad y benchmark BTS/FAA. El resto es operacional en vivo, mismo
criterio que DB-01/DB-02 — la spec de este dashboard puntualmente ya pide
consultar "vuelos en monitoreo" directo (no hay tabla ClickHouse a nivel de
vuelo individual, son ~cientos de vuelos activos, no agregados mensuales).

Nota sobre "vuelos_monitoreo": no existe esa colección — es el mismo dato
que ya usa `/backoffice/vuelos/activos` (`vuelos_catalogo` activos +
riesgo calculado en vivo por aerolínea, ver `router_monitor.py`), se
reutiliza esa función en vez de reimplementar el cálculo de riesgo.

"Notificaciones enviadas": la spec pide `estado=enviado`, pero
`notificaciones.estado_envio` no está poblado en ningún registro real del
proyecto — se cuenta la existencia del registro (cada notificación creada
implica que se intentó enviar) en vez de filtrar por un campo vacío.
"""

from __future__ import annotations

import datetime

from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.shared.clickhouse_client import query_dicts
from app.vuelos.router_monitor import _vuelos_activos_con_riesgo


async def obtener_datos_disrupciones(desde: datetime.date, hasta: datetime.date) -> dict:
    # ── Grupo A — estado actual (en vivo) ─────────────────────────────
    vuelos_riesgo = await _vuelos_activos_con_riesgo(None, None, None)
    vuelos_en_monitoreo = len(vuelos_riesgo)
    vuelos_riesgo_alto = sum(1 for v in vuelos_riesgo if v["nivel_riesgo"] == "alto")

    disrep = DisrupcionesRepository()
    notificaciones_periodo = await disrep.listar_notificaciones(desde=desde.isoformat(), hasta=hasta.isoformat())

    # ── Grupo B — efectividad (ClickHouse, mensual) ───────────────────
    filas_disrup = query_dicts(
        """
        SELECT aerolinea_nombre, sum(total_notificaciones) AS total_notificaciones,
               sum(exitosas) AS exitosas, sum(con_accion_pasajero) AS con_accion_pasajero,
               avg(otp_benchmark_bts) AS otp_benchmark_bts
        FROM agg_disrupciones_aerolinea_ruta
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY aerolinea_nombre ORDER BY total_notificaciones DESC
        """,
        {"desde": desde, "hasta": hasta},
    )
    total_exitosas = sum(f["exitosas"] for f in filas_disrup)
    total_con_accion = sum(f["con_accion_pasajero"] for f in filas_disrup)
    total_fallidas = 0
    filas_fallidas = query_dicts(
        """
        SELECT sum(fallidas) AS fallidas FROM agg_disrupciones_aerolinea_ruta
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    if filas_fallidas:
        total_fallidas = filas_fallidas[0]["fallidas"] or 0
    efectividad_pct = round(total_con_accion / total_exitosas * 100, 2) if total_exitosas else 0.0

    # ── Grupo C — histórico y soporte ─────────────────────────────────
    disrupciones_raw = await disrep.listar_disrupciones()
    hoy_semana = datetime.date.today()
    inicio_8_semanas = hoy_semana - datetime.timedelta(weeks=8)
    conteo_semana: dict[str, int] = {}
    for d in disrupciones_raw:
        fecha_str = d.get("fecha_deteccion") or d.get("created")
        if not fecha_str:
            continue
        fecha = datetime.datetime.fromisoformat(fecha_str.replace("Z", "+00:00")).date()
        if fecha < inicio_8_semanas:
            continue
        semana_inicio = fecha - datetime.timedelta(days=fecha.weekday())
        clave = semana_inicio.isoformat()
        conteo_semana[clave] = conteo_semana.get(clave, 0) + 1
    disrupciones_por_semana = [{"semana": k, "total": v} for k, v in sorted(conteo_semana.items())]

    casos_abiertos = await CentroAyudaRepository().listar_casos(estado="abierto")

    filas_satisfaccion = query_dicts(
        """
        SELECT avg(calificacion_promedio) AS promedio, sum(total_consultas) AS total_consultas
        FROM agg_satisfaccion_soporte
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    satisfaccion = filas_satisfaccion[0] if filas_satisfaccion else {"promedio": 0, "total_consultas": 0}

    return {
        "vuelos_en_monitoreo": vuelos_en_monitoreo,
        "vuelos_riesgo_alto": vuelos_riesgo_alto,
        "notificaciones_enviadas": len(notificaciones_periodo),
        "efectividad_pct": efectividad_pct,
        "total_exitosas": total_exitosas,
        "total_fallidas": total_fallidas,
        "disrupciones_por_aerolinea": filas_disrup,
        "disrupciones_por_semana": disrupciones_por_semana,
        "casos_escalados_abiertos": len(casos_abiertos),
        "satisfaccion_promedio": round(satisfaccion["promedio"] or 0, 2),
        "satisfaccion_total_consultas": satisfaccion["total_consultas"] or 0,
    }
