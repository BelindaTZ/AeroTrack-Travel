"""DS-00 a DS-03 — dashboards estratégicos (Fase C, docs/estrategico-auditoria.md).

Reusa las 3 VIEWs (`v_resumen_ejecutivo`, `v_rendimiento_oferta`,
`v_disrupciones_global`) y la tabla `agg_uso_asistente_ia` de Fase B, más
`agg_conversion_busqueda_reserva`/`agg_alertas_conversion`/
`agg_segmentos_pasajero` (tácticas, sin VIEW propia porque DS-00/03 los
consumen tal cual). Para lo que no tiene agregado en ClickHouse (vuelos en
monitoreo hoy, casos escalados abiertos, alertas de precio activas por
destino) se reutilizan las MISMAS funciones que ya usan los dashboards
tácticos (`_vuelos_activos_con_riesgo`, `CentroAyudaRepository`,
`ReservasRepository.listar_todas_alertas`) en vez de reimplementar la
consulta — mismo criterio que `disrupciones_service.py`/`clientes_service.py`.
"""

from __future__ import annotations

import datetime

from app.asistente_ia.repositories.asistente_repo import AsistenteRepository
from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.shared.clickhouse_client import query_dicts
from app.vuelos.router_monitor import _vuelos_activos_con_riesgo

CLAVE_CAC_VALOR = "cac_digital_actual"
CLAVE_CAC_PERIODO = "cac_digital_periodo"


def _rango_anterior(desde: datetime.date, hasta: datetime.date) -> tuple[datetime.date, datetime.date]:
    duracion = (hasta - desde).days + 1
    return desde - datetime.timedelta(days=duracion), desde - datetime.timedelta(days=1)


def _num(valor) -> float:
    """ClickHouse `avg()` sobre un grupo vacío devuelve NaN, no NULL — `nan
    or 0.0` no lo detecta porque NaN es truthy en Python. `json.dumps` no
    serializa NaN (no es JSON válido), así que hay que sanearlo acá antes
    de devolver la respuesta."""
    if valor is None or (isinstance(valor, float) and valor != valor):
        return 0.0
    return float(valor)


async def _cac_digital() -> dict:
    repo = SeguridadRepository()
    valor = await repo.get_config(CLAVE_CAC_VALOR)
    periodo = await repo.get_config(CLAVE_CAC_PERIODO)
    return {
        "valor": float(valor["valor"]) if valor else 0.0,
        "periodo": periodo["valor"] if periodo and periodo["valor"] != "—" else None,
        "ingresado_manualmente": True,
    }


async def obtener_datos_cockpit(desde: datetime.date, hasta: datetime.date) -> dict:
    # ── OE-1 (Financiera) — ingresos totales + variación vs período anterior
    filas_ingresos = query_dicts(
        """
        SELECT tipo_producto, sum(total_reservas) AS total_reservas, sum(ingresos_netos) AS ingresos_netos
        FROM agg_ingresos_por_producto_mes
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY tipo_producto ORDER BY ingresos_netos DESC
        """,
        {"desde": desde, "hasta": hasta},
    )
    ingresos_totales = sum(f["ingresos_netos"] for f in filas_ingresos)
    reservas_totales_ingresos = sum(f["total_reservas"] for f in filas_ingresos)

    desde_ant, hasta_ant = _rango_anterior(desde, hasta)
    filas_ingresos_ant = query_dicts(
        """
        SELECT sum(ingresos_netos) AS ingresos_netos
        FROM agg_ingresos_por_producto_mes
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde_ant, "hasta": hasta_ant},
    )
    ingresos_periodo_anterior = (filas_ingresos_ant[0]["ingresos_netos"] or 0.0) if filas_ingresos_ant else 0.0
    variacion_ingresos_pct = (
        round((ingresos_totales - ingresos_periodo_anterior) / ingresos_periodo_anterior * 100, 2)
        if ingresos_periodo_anterior else None
    )

    # ── OE-2 (Cliente) — reservas confirmadas + conversión búsqueda→reserva
    filas_conversion = query_dicts(
        """
        SELECT sum(total_busquedas) AS busquedas, sum(total_confirmadas) AS confirmadas
        FROM agg_conversion_busqueda_reserva
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    conv = filas_conversion[0] if filas_conversion else {"busquedas": 0, "confirmadas": 0}
    tasa_conversion = round(conv["confirmadas"] / conv["busquedas"] * 100, 2) if conv["busquedas"] else 0.0

    # ── OE-3 (Procesos) — efectividad de disrupciones + vuelos en monitoreo (vivo)
    filas_disrup = query_dicts(
        """
        SELECT sum(exitosas) AS exitosas, sum(con_accion_pasajero) AS con_accion
        FROM agg_disrupciones_aerolinea_ruta
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    disrup = filas_disrup[0] if filas_disrup else {"exitosas": 0, "con_accion": 0}
    tasa_efectividad = round(disrup["con_accion"] / disrup["exitosas"] * 100, 2) if disrup["exitosas"] else 0.0
    vuelos_riesgo = await _vuelos_activos_con_riesgo(None, None, None)

    # ── OE-4 (Aprendizaje) — % calificación positiva del asistente IA + consultas
    filas_ia = query_dicts(
        """
        SELECT total_consultas, total_calificadas, pct_calificacion_positiva
        FROM agg_uso_asistente_ia
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    total_consultas_ia = sum(f["total_consultas"] for f in filas_ia)
    total_calificadas_ia = sum(f["total_calificadas"] for f in filas_ia)
    # Promedio ponderado por volumen de calificaciones de cada mes, no un
    # promedio simple entre meses (un mes con 1 calificación no debe pesar
    # igual que uno con 50) — mismo criterio de "no fabricar precisión donde
    # no la hay" que el resto del proyecto.
    suma_positivas_ponderada = sum(f["pct_calificacion_positiva"] * f["total_calificadas"] for f in filas_ia)
    pct_calificacion_positiva = (
        round(suma_positivas_ponderada / total_calificadas_ia, 2) if total_calificadas_ia else 0.0
    )

    # ── Centro — tendencia de ingresos, últimos 6 períodos disponibles
    tendencia = query_dicts(
        "SELECT periodo, ingresos_totales FROM v_resumen_ejecutivo ORDER BY periodo DESC LIMIT 6"
    )
    tendencia.reverse()

    # ── Fila inferior
    ingreso_promedio_reserva = (
        round(ingresos_totales / reservas_totales_ingresos, 2) if reservas_totales_ingresos else 0.0
    )
    top_3_productos = [
        {"tipo_producto": f["tipo_producto"], "ingresos": round(f["ingresos_netos"], 2)}
        for f in filas_ingresos[:3]
    ]

    return {
        "oe1_ingresos_totales": round(ingresos_totales, 2),
        "oe1_variacion_pct": variacion_ingresos_pct,
        "oe2_reservas_confirmadas": conv["confirmadas"] or 0,
        "oe2_tasa_conversion": tasa_conversion,
        "oe3_tasa_efectividad": tasa_efectividad,
        "oe3_vuelos_monitoreados_hoy": len(vuelos_riesgo),
        "oe4_pct_calificacion_positiva": pct_calificacion_positiva,
        "oe4_total_consultas": total_consultas_ia,
        "tendencia_ingresos": tendencia,
        "cac_digital": await _cac_digital(),
        "ingreso_promedio_reserva": ingreso_promedio_reserva,
        "top_3_productos": top_3_productos,
    }


async def obtener_datos_oferta(desde: datetime.date, hasta: datetime.date) -> dict:
    """DS-01. `v_rendimiento_oferta` es una fila por (periodo, tipo_producto)
    — para un rango de varios meses se reagrega acá mismo (una VIEW de
    ClickHouse es una consulta guardada, se puede volver a agregar sobre
    ella sin problema). `take_rate_pct` se recalcula desde comisiones/
    ingresos_brutos crudos (no promediando el `take_rate_pct` ya mensual de
    la VIEW) para que sea exacto sobre el rango completo, no un promedio de
    promedios."""
    filas_producto = query_dicts(
        """
        SELECT tipo_producto, sum(total_reservas) AS total_reservas,
               sum(ingresos_brutos) AS ingresos_brutos, sum(ingresos_netos) AS ingresos_netos,
               sum(comisiones) AS comisiones
        FROM agg_ingresos_por_producto_mes
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY tipo_producto ORDER BY ingresos_netos DESC
        """,
        {"desde": desde, "hasta": hasta},
    )
    metricas_por_producto = []
    for f in filas_producto:
        ticket_promedio = round(f["ingresos_netos"] / f["total_reservas"], 2) if f["total_reservas"] else 0.0
        take_rate = round(f["comisiones"] / f["ingresos_brutos"] * 100, 2) if f["ingresos_brutos"] else 0.0
        metricas_por_producto.append({
            "tipo_producto": f["tipo_producto"], "total_reservas": f["total_reservas"],
            "ingresos_netos": round(f["ingresos_netos"], 2), "ticket_promedio": ticket_promedio, "take_rate_pct": take_rate,
        })

    filas_conversion = query_dicts(
        """
        SELECT tipo_producto, sum(total_busquedas) AS busquedas, sum(total_confirmadas) AS confirmadas
        FROM agg_conversion_busqueda_reserva
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY tipo_producto
        """,
        {"desde": desde, "hasta": hasta},
    )
    tasas_conversion = [
        {"tipo_producto": f["tipo_producto"], "tasa": round(f["confirmadas"] / f["busquedas"] * 100, 2) if f["busquedas"] else 0.0}
        for f in filas_conversion
    ]
    producto_mayor_conversion = max(tasas_conversion, key=lambda x: x["tasa"])["tipo_producto"] if tasas_conversion else None

    # Margen promedio de paquetes — mismo criterio que paquetes_service.py
    # (DB-07): avg() simple sobre las filas del período, no ponderado.
    filas_margen = query_dicts(
        """
        SELECT avg(margen_porcentaje) AS margen_pct
        FROM agg_paquetes_margen_mes
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    margen_promedio_paquetes = round(_num(filas_margen[0]["margen_pct"]), 2) if filas_margen else 0.0

    tendencia = query_dicts(
        "SELECT periodo, ingresos_totales FROM v_resumen_ejecutivo ORDER BY periodo DESC LIMIT 6"
    )
    tendencia.reverse()

    return {
        "producto_mayor_ingreso": metricas_por_producto[0]["tipo_producto"] if metricas_por_producto else None,
        "producto_mayor_conversion": producto_mayor_conversion,
        "margen_promedio_paquetes": margen_promedio_paquetes,
        "ingresos_por_producto": [
            {"tipo_producto": m["tipo_producto"], "ingresos_netos": m["ingresos_netos"], "total_reservas": m["total_reservas"]}
            for m in metricas_por_producto
        ],
        "tendencia_ingresos": tendencia,
        "metricas_por_producto": metricas_por_producto,
    }


async def obtener_datos_disrupciones_global(desde: datetime.date, hasta: datetime.date) -> dict:
    """DS-02. "OTP promedio ... vs. benchmark BTS/FAA" usa
    `otp_benchmark_bts` de `agg_disrupciones_aerolinea_ruta` (mismo campo
    que ya usa DB-03 táctico) — es el histórico BTS/FAA de las rutas con
    disrupciones detectadas en el período, no un OTP "en vivo" separado
    (ese dato no existe fuera de ese campo)."""
    filas_periodo = query_dicts(
        """
        SELECT sum(total_notificaciones) AS total_notificaciones, sum(exitosas) AS exitosas,
               sum(con_accion_pasajero) AS con_accion, avg(otp_benchmark_bts) AS otp_benchmark
        FROM agg_disrupciones_aerolinea_ruta
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    p = filas_periodo[0] if filas_periodo else {"total_notificaciones": 0, "exitosas": 0, "con_accion": 0, "otp_benchmark": 0}
    tasa_efectividad = round(p["con_accion"] / p["exitosas"] * 100, 2) if p["exitosas"] else 0.0

    tendencia = query_dicts(
        """
        SELECT periodo, tasa_efectividad_global FROM v_disrupciones_global
        ORDER BY periodo DESC LIMIT 6
        """
    )
    tendencia.reverse()

    filas_satisfaccion = query_dicts(
        """
        SELECT avg(calificacion_promedio) AS promedio FROM agg_satisfaccion_soporte
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    satisfaccion_promedio = round(_num(filas_satisfaccion[0]["promedio"]), 2) if filas_satisfaccion else 0.0

    top_aerolineas = query_dicts(
        """
        SELECT aerolinea_nombre, sum(total_notificaciones) AS total_notificaciones
        FROM agg_disrupciones_aerolinea_ruta
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        GROUP BY aerolinea_nombre ORDER BY total_notificaciones DESC LIMIT 5
        """,
        {"desde": desde, "hasta": hasta},
    )

    casos_abiertos = await CentroAyudaRepository().listar_casos(estado="abierto")

    return {
        "notificaciones_enviadas": p["total_notificaciones"] or 0,
        "tasa_efectividad": tasa_efectividad,
        "otp_benchmark_bts": round(_num(p["otp_benchmark"]), 2),
        "tendencia_efectividad": tendencia,
        "con_accion": p["con_accion"] or 0,
        "sin_accion": max((p["exitosas"] or 0) - (p["con_accion"] or 0), 0),
        "satisfaccion_promedio": satisfaccion_promedio,
        "casos_escalados_abiertos": len(casos_abiertos),
        "top_aerolineas": top_aerolineas,
    }


async def obtener_datos_inteligencia(desde: datetime.date, hasta: datetime.date) -> dict:
    """DS-03. Consultas por semana necesitan granularidad que
    `agg_uso_asistente_ia` no tiene (mensual) — se calculan en vivo, mismo
    criterio que `demanda_service.py`/DB-06. Segmentos de pasajero y top
    destinos en alertas son snapshots sin filtro de período, igual que
    DB-05/DB-12 tácticos (`clientes_service.py`)."""
    filas_ia = query_dicts(
        """
        SELECT total_consultas, total_calificadas, pct_calificacion_positiva
        FROM agg_uso_asistente_ia
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    total_consultas = sum(f["total_consultas"] for f in filas_ia)
    total_calificadas = sum(f["total_calificadas"] for f in filas_ia)
    suma_positivas_ponderada = sum(f["pct_calificacion_positiva"] * f["total_calificadas"] for f in filas_ia)
    pct_calificacion_positiva = round(suma_positivas_ponderada / total_calificadas, 2) if total_calificadas else 0.0

    # GROUP BY periodo (no un SELECT directo) porque `agg_uso_asistente_ia`
    # es ReplacingMergeTree — sin agregar, corridas horarias todavía no
    # mergeadas del mismo mes aparecerían como filas duplicadas en el eje X.
    tendencia_calificacion = query_dicts(
        """
        SELECT periodo,
               sum(pct_calificacion_positiva * total_calificadas) / nullif(sum(total_calificadas), 0) AS pct_calificacion_positiva
        FROM agg_uso_asistente_ia
        GROUP BY periodo ORDER BY periodo DESC LIMIT 6
        """
    )
    for f in tendencia_calificacion:
        f["pct_calificacion_positiva"] = round(f["pct_calificacion_positiva"] or 0.0, 2)
    tendencia_calificacion.reverse()

    filas_alertas = query_dicts(
        """
        SELECT sum(total_alertas_activas) AS activas, sum(total_conversiones) AS conversiones
        FROM agg_alertas_conversion
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    alertas = filas_alertas[0] if filas_alertas else {"activas": 0, "conversiones": 0}
    tasa_conversion_alertas = round(alertas["conversiones"] / alertas["activas"] * 100, 2) if alertas["activas"] else 0.0

    filas_segmento = query_dicts("SELECT segmento, count() AS total FROM agg_segmentos_pasajero GROUP BY segmento")

    # ── En vivo — consultas por semana + total alertas activas + top destinos
    mensajes = await AsistenteRepository().listar_todos_mensajes()
    consultas = [
        m for m in mensajes
        if m.get("rol") == "usuario" and m.get("fecha") and desde.isoformat() <= m["fecha"][:10] <= hasta.isoformat()
    ]
    semana_conteo: dict[str, int] = {}
    for m in consultas:
        fecha = datetime.datetime.fromisoformat(m["fecha"].replace("Z", "+00:00")).date()
        inicio_semana = fecha - datetime.timedelta(days=fecha.weekday())
        semana_conteo[inicio_semana.isoformat()] = semana_conteo.get(inicio_semana.isoformat(), 0) + 1
    consultas_por_semana = [{"semana": k, "total": v} for k, v in sorted(semana_conteo.items())]

    reservas_repo = ReservasRepository()
    alertas_todas = await reservas_repo.listar_todas_alertas()
    alertas_activas = [a for a in alertas_todas if a.get("activa")]
    destino_conteo: dict[str, int] = {}
    for a in alertas_activas:
        destino_conteo[a["destino_codigo"]] = destino_conteo.get(a["destino_codigo"], 0) + 1
    top_5_destinos = sorted(
        [{"destino": k, "total": v} for k, v in destino_conteo.items()], key=lambda x: x["total"], reverse=True
    )[:5]

    return {
        "total_consultas": total_consultas,
        "pct_calificacion_positiva": pct_calificacion_positiva,
        "alertas_activas_total": len(alertas_activas),
        "consultas_por_semana": consultas_por_semana,
        "tendencia_calificacion": tendencia_calificacion,
        "segmentos": filas_segmento,
        "tasa_conversion_alertas": tasa_conversion_alertas,
        "top_5_destinos_alertas": top_5_destinos,
    }
