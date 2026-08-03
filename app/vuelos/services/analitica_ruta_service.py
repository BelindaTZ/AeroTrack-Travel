"""DB-04 — Diferenciador Analítico de Vuelos (vista del pasajero).

Lee de ClickHouse (`agg_otp_aerolinea_mes`, `agg_causas_retraso_mes`,
`agg_otp_dia_semana`, cargadas por `aerotrack_travel_etl_dims`) el
historial real BTS/FAA 2021-2025 para una ruta origen-destino específica.
Sin filtro de período manual (spec): siempre usa todo el histórico
disponible en esas tablas.
"""

from __future__ import annotations

from app.shared.clickhouse_client import query_dicts

_CAUSA_LEGIBLE = {
    "carrier": "Problemas de la aerolínea (tripulación, mantenimiento)",
    "weather": "Clima",
    "nas": "Congestión del sistema de control aéreo",
    "security": "Seguridad",
    "late_aircraft": "Llegada tardía de la aeronave anterior",
}

_DIAS_SEMANA = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado", 7: "Domingo"}


def obtener_analitica_ruta(origen: str, destino: str) -> dict:
    por_aerolinea = query_dicts(
        """
        SELECT aerolinea_codigo, any(aerolinea_nombre) AS aerolinea_nombre,
               sum(total_vuelos) AS total_vuelos, sum(vuelos_a_tiempo) AS vuelos_a_tiempo
        FROM agg_otp_aerolinea_mes
        WHERE origen = %(origen)s AND destino = %(destino)s
        GROUP BY aerolinea_codigo
        ORDER BY vuelos_a_tiempo / total_vuelos DESC
        """,
        {"origen": origen, "destino": destino},
    )

    if not por_aerolinea:
        return {"cobertura": False}

    total_vuelos = sum(a["total_vuelos"] for a in por_aerolinea)
    total_a_tiempo = sum(a["vuelos_a_tiempo"] for a in por_aerolinea)
    otp_historico = round(total_a_tiempo / total_vuelos * 100, 1) if total_vuelos else 0.0

    for a in por_aerolinea:
        a["otp_porcentaje"] = round(a["vuelos_a_tiempo"] / a["total_vuelos"] * 100, 1) if a["total_vuelos"] else 0.0
    mejor_aerolinea = por_aerolinea[0]

    por_mes = query_dicts(
        """
        SELECT toMonth(periodo) AS mes, sum(total_vuelos) AS total_vuelos, sum(vuelos_a_tiempo) AS vuelos_a_tiempo
        FROM agg_otp_aerolinea_mes
        WHERE origen = %(origen)s AND destino = %(destino)s
        GROUP BY mes ORDER BY mes
        """,
        {"origen": origen, "destino": destino},
    )
    for m in por_mes:
        m["otp_porcentaje"] = round(m["vuelos_a_tiempo"] / m["total_vuelos"] * 100, 1) if m["total_vuelos"] else 0.0

    por_dia_semana = query_dicts(
        """
        SELECT dia_semana, sum(total_vuelos) AS total_vuelos, sum(vuelos_a_tiempo) AS vuelos_a_tiempo
        FROM agg_otp_dia_semana
        WHERE origen = %(origen)s AND destino = %(destino)s
        GROUP BY dia_semana ORDER BY dia_semana
        """,
        {"origen": origen, "destino": destino},
    )
    for d in por_dia_semana:
        d["dia_legible"] = _DIAS_SEMANA.get(d["dia_semana"], str(d["dia_semana"]))
        d["otp_porcentaje"] = round(d["vuelos_a_tiempo"] / d["total_vuelos"] * 100, 1) if d["total_vuelos"] else 0.0

    causas = query_dicts(
        """
        SELECT causa, sum(total_casos) AS total_casos
        FROM agg_causas_retraso_mes
        WHERE origen = %(origen)s AND destino = %(destino)s
        GROUP BY causa ORDER BY total_casos DESC
        """,
        {"origen": origen, "destino": destino},
    )
    total_casos = sum(c["total_casos"] for c in causas) or 1
    for c in causas:
        c["causa_legible"] = _CAUSA_LEGIBLE.get(c["causa"], c["causa"])
        c["porcentaje"] = round(c["total_casos"] / total_casos * 100, 1)
    causa_principal = causas[0]["causa_legible"] if causas else None

    return {
        "cobertura": True,
        "otp_historico": otp_historico,
        "mejor_aerolinea": {"nombre": mejor_aerolinea["aerolinea_nombre"], "otp_porcentaje": mejor_aerolinea["otp_porcentaje"]},
        "causa_principal": causa_principal,
        "por_aerolinea": por_aerolinea,
        "por_mes": por_mes,
        "por_dia_semana": por_dia_semana,
        "causas": causas,
    }
