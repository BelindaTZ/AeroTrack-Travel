"""DB-08 — Catálogo y Rutas de Vuelos.

`agg_conversion_busqueda_reserva` no tiene desglose por ruta ni por
hora/día (solo periodo+tipo_producto) — todo lo que la spec pide "por
ruta" o "por hora del día" (ruta más buscada, top 10 rutas, mapa de calor
día×hora) sale en vivo de `busquedas_recientes.criterios` (JSON con
origen/destino solo para tipo_producto="vuelo"; otros tipos de producto
no tienen ese concepto). Dataset muy chico (~16 búsquedas totales en el
proyecto, ver limitación ya documentada en DB-01) — es esperable que estas
visualizaciones salgan dispersas, no es un bug.
"""

from __future__ import annotations

import datetime

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.shared.clickhouse_client import query_dicts
from app.shared.minio_catalog_reader import fecha_publicacion
from app.vuelos.repositories.airflow_client import AirflowNoDisponible, estado_dag


async def obtener_datos_catalogo_rutas(desde: datetime.date, hasta: datetime.date) -> dict:
    busquedas = await CuentaRepository().listar_todas_busquedas()
    busquedas_periodo = [
        b for b in busquedas if b.get("fecha") and desde.isoformat() <= b["fecha"][:10] <= hasta.isoformat()
    ]

    por_tipo: dict[str, int] = {}
    por_ruta: dict[str, int] = {}
    por_dia_hora: dict[tuple[int, int], int] = {}
    for b in busquedas_periodo:
        tipo = b.get("tipo_producto") or "desconocido"
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

        criterios = b.get("criterios") or {}
        if tipo == "vuelo" and criterios.get("origen") and criterios.get("destino"):
            ruta = f"{criterios['origen']}-{criterios['destino']}"
            por_ruta[ruta] = por_ruta.get(ruta, 0) + 1

        fecha_str = b.get("fecha")
        if fecha_str:
            fecha = datetime.datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
            clave = (fecha.weekday(), fecha.hour)
            por_dia_hora[clave] = por_dia_hora.get(clave, 0) + 1

    ruta_mas_buscada = max(por_ruta.items(), key=lambda x: x[1])[0] if por_ruta else None
    top_10_rutas = sorted(
        [{"ruta": k, "busquedas": v} for k, v in por_ruta.items()], key=lambda x: x["busquedas"], reverse=True
    )[:10]

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

    try:
        estado = await estado_dag()
        ultima_corrida = estado.get("ultima_corrida") or {}
        catalogo_estado = ultima_corrida.get("state", "sin corridas")
    except AirflowNoDisponible:
        catalogo_estado = "airflow no disponible"
    ultima_actualizacion = await fecha_publicacion("vuelos_catalogo")

    return {
        "ruta_mas_buscada": ruta_mas_buscada,
        "tasa_conversion_promedio": tasa_conversion,
        "catalogo_estado": catalogo_estado,
        "catalogo_ultima_actualizacion": ultima_actualizacion,
        "top_10_rutas": top_10_rutas,
        "busquedas_por_tipo": [{"tipo_producto": k, "total": v} for k, v in por_tipo.items()],
        "mapa_calor_dia_hora": [{"dia": d, "hora": h, "total": v} for (d, h), v in por_dia_hora.items()],
    }
