"""DB-05 — Captación y Retención de Pasajeros.

`agg_segmentos_pasajero` (ClickHouse) para segmentos nuevo/recurrente/
frecuente. El resto ("nuevos pasajeros del período", canal de captación,
tasa de activación) necesita filtrar por fecha de PRIMERA reserva contra
el período elegido — eso es filtrado en vivo sobre `reservas`, ClickHouse
no tiene ese corte por período (la tabla ya viene con `primera_reserva`
fija por pasajero, sin filtro dinámico posible en SQL sin traer todo)."""

from __future__ import annotations

import datetime

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.clickhouse_client import query_dicts


def _rango_anterior(desde: datetime.date, hasta: datetime.date) -> tuple[datetime.date, datetime.date]:
    duracion = (hasta - desde).days + 1
    return desde - datetime.timedelta(days=duracion), desde - datetime.timedelta(days=1)


async def obtener_datos_clientes(desde: datetime.date, hasta: datetime.date) -> dict:
    reservas_repo = ReservasRepository()
    reservas = await reservas_repo.listar_todas()
    pasajeros = await PasajerosRepository().listar_todos_pasajeros()
    pasajero_por_id = {p["id"]: p for p in pasajeros}

    primera_reserva_por_pasajero: dict[str, datetime.date] = {}
    for r in reservas:
        pid = r.get("pasajero_titular_id")
        if not pid or not r.get("fecha_reserva"):
            continue
        fecha = datetime.datetime.fromisoformat(r["fecha_reserva"].replace("Z", "+00:00")).date()
        if pid not in primera_reserva_por_pasajero or fecha < primera_reserva_por_pasajero[pid]:
            primera_reserva_por_pasajero[pid] = fecha

    desde_ant, hasta_ant = _rango_anterior(desde, hasta)
    nuevos_periodo = [pid for pid, f in primera_reserva_por_pasajero.items() if desde <= f <= hasta]
    nuevos_periodo_anterior = [pid for pid, f in primera_reserva_por_pasajero.items() if desde_ant <= f <= hasta_ant]

    canal_conteo: dict[str, int] = {}
    for pid in nuevos_periodo:
        canal = (pasajero_por_id.get(pid) or {}).get("canal_registro")
        if canal:
            canal_conteo[canal] = canal_conteo.get(canal, 0) + 1
    canal_top = max(canal_conteo.items(), key=lambda x: x[1])[0] if canal_conteo else None

    tasa_activacion = round(len(primera_reserva_por_pasajero) / len(pasajeros) * 100, 2) if pasajeros else 0.0

    dias_periodo = [(desde + datetime.timedelta(days=i)) for i in range((hasta - desde).days + 1)]
    semana_conteo: dict[str, int] = {}
    for pid in nuevos_periodo:
        fecha = primera_reserva_por_pasajero[pid]
        inicio_semana = fecha - datetime.timedelta(days=fecha.weekday())
        semana_conteo[inicio_semana.isoformat()] = semana_conteo.get(inicio_semana.isoformat(), 0) + 1
    nuevos_por_semana = [{"semana": k, "total": v} for k, v in sorted(semana_conteo.items())]

    # ── ClickHouse — segmentos ─────────────────────────────────────────
    filas_segmento = query_dicts("SELECT segmento, count() AS total FROM agg_segmentos_pasajero GROUP BY segmento")

    # ── Alertas de precio (en vivo — snapshot actual, no filtrado por período,
    #    igual que "reservas por expirar" en DB-01) ────────────────────
    alertas = await reservas_repo.listar_todas_alertas()
    alertas_activas = [a for a in alertas if a.get("activa")]
    destino_conteo: dict[str, int] = {}
    for a in alertas_activas:
        destino_conteo[a["destino_codigo"]] = destino_conteo.get(a["destino_codigo"], 0) + 1
    top_destinos = sorted(
        [{"destino": k, "total": v} for k, v in destino_conteo.items()], key=lambda x: x["total"], reverse=True
    )[:10]

    filas_conversion = query_dicts(
        """
        SELECT sum(total_alertas_activas) AS activas, sum(total_conversiones) AS conversiones
        FROM agg_alertas_conversion
        WHERE periodo >= toStartOfMonth(toDate(%(desde)s)) AND periodo <= toStartOfMonth(toDate(%(hasta)s))
        """,
        {"desde": desde, "hasta": hasta},
    )
    conv = filas_conversion[0] if filas_conversion else {"activas": 0, "conversiones": 0}
    tasa_conversion_alertas = round(conv["conversiones"] / conv["activas"] * 100, 2) if conv["activas"] else 0.0

    return {
        "nuevos_periodo": len(nuevos_periodo),
        "nuevos_periodo_anterior": len(nuevos_periodo_anterior),
        "tasa_activacion": tasa_activacion,
        "canal_top": canal_top,
        "segmentos": filas_segmento,
        "nuevos_por_semana": nuevos_por_semana,
        "alertas_activas_total": len(alertas_activas),
        "tasa_conversion_alertas": tasa_conversion_alertas,
        "top_destinos_alertas": top_destinos,
    }
