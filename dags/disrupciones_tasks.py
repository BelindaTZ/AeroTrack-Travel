"""
AeroTrack Travel — Simulador estadístico de riesgo de disrupción (CU-O39)
============================================================================
Primera de las tres fuentes de detección descritas en el documento
empresarial (sección 5, OT-2.1): para reservas/vuelos lejanos a la fecha
de viaje, se estima probabilidad de disrupción con el histórico BTS/FAA
(agg_otp_aerolinea_mes + agg_causas_retraso_mes), en vez de consultar una
API de estado real (CU-O40, que solo se activa cerca de la fecha de vuelo,
umbral configurable en configuracion_sistema).

Principio E2 de la constitución (deduplicación entre fuentes): esta tarea
nunca crea una segunda fila para el mismo vuelo — actualiza la disrupción
existente de esta misma fuente si ya existe.

Fuera de alcance de esta tarea (adrede): el envío de la notificación al
pasajero (CU-O43) depende del servicio de notificaciones (canal email/SMS,
CU-O60), que todavía no está implementado en la capa de aplicación.
"""

from __future__ import annotations

import datetime

import pocketbase_client as pb
from minio_dims_reader import read_parquet

UMBRAL_RIESGO_PCT_DEFAULT = 20.0
CAUSAS = ["carrierdelay", "weatherdelay", "nasdelay", "securitydelay", "lateaircraftdelay"]
CAUSAS_LEGIBLES = {
    "carrierdelay": "la propia aerolínea",
    "weatherdelay": "condiciones climáticas",
    "nasdelay": "el sistema nacional de espacio aéreo",
    "securitydelay": "procesos de seguridad",
    "lateaircraftdelay": "la llegada tardía de la aeronave anterior",
}


def _otp_por_aerolinea() -> dict[str, float]:
    """Promedio de otp_pct de los últimos 12 registros mensuales disponibles
    por aerolínea (histórico BTS/FAA, agg_otp_aerolinea_mes)."""
    df = read_parquet("agg_otp_aerolinea_mes", ["carrier", "year", "month", "otp_pct"])
    df = df.sort_values(["carrier", "year", "month"])
    ultimos = df.groupby("carrier").tail(12)
    return ultimos.groupby("carrier")["otp_pct"].mean().round(2).to_dict()


def _causa_dominante_por_aerolinea() -> dict[str, str]:
    """Causa de retraso con mayor suma acumulada por aerolínea (agg_causas_retraso_mes)."""
    df = read_parquet("agg_causas_retraso_mes", ["carrier"] + CAUSAS)
    disponibles = [c for c in CAUSAS if c in df.columns]
    if not disponibles:
        return {}
    sums = df.groupby("carrier")[disponibles].sum()
    dominante = sums.idxmax(axis=1)
    return dominante.to_dict()


def estimar_riesgo_disrupcion() -> dict:
    """CU-O39. Recorre vuelos_catalogo 'programados' fuera del umbral de
    API real y crea/actualiza una fila en disrupciones cuando el riesgo
    histórico de la aerolínea supera el umbral configurado."""
    umbral_horas = int(pb.get_config("disrupciones.umbral_api_real_horas", "72"))
    umbral_riesgo = float(pb.get_config("simulador_disrupciones.umbral_riesgo_pct", str(UMBRAL_RIESGO_PCT_DEFAULT)))

    otp = _otp_por_aerolinea()
    causa_dominante = _causa_dominante_por_aerolinea()

    limite_lejania = datetime.datetime.utcnow() + datetime.timedelta(hours=umbral_horas)
    vuelos = pb.list_all("vuelos_catalogo", filter_='estado="programado"')
    aerolineas = {a["id"]: a for a in pb.list_all("aerolineas")}

    evaluados = altos = actualizados = resueltos = 0

    for v in vuelos:
        try:
            fecha_salida = datetime.datetime.strptime(v["fecha_salida"][:10], "%Y-%m-%d")
        except (ValueError, KeyError):
            continue
        if fecha_salida <= limite_lejania:
            continue  # ya está en ventana de API real (CU-O40), no le toca al simulador

        aerolinea = aerolineas.get(v["aerolinea_id"])
        if not aerolinea:
            continue
        iata = aerolinea["codigo_iata"]
        otp_pct = otp.get(iata)
        if otp_pct is None:
            continue

        evaluados += 1
        riesgo = round(100 - otp_pct, 2)
        existente = pb.get_first(
            "disrupciones", f'vuelo_id="{v["id"]}" && fuente_deteccion="simulador_estadistico"'
        )

        if riesgo >= umbral_riesgo:
            altos += 1
            causa = causa_dominante.get(iata)
            detalle = (
                f"Riesgo estimado {riesgo}% según OTP histórico de {iata} "
                f"(últimos 12 meses BTS/FAA)."
                + (f" Causa dominante: {CAUSAS_LEGIBLES.get(causa, causa)}." if causa else "")
            )
            payload = {
                "probabilidad": riesgo,
                "detalle": detalle,
                "estado": "activa",
                "fecha_deteccion": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z"),
            }
            if existente:
                pb.update("disrupciones", existente["id"], payload)
                actualizados += 1
            else:
                pb.create("disrupciones", {
                    "vuelo_id": v["id"],
                    "fuente_deteccion": "simulador_estadistico",
                    "tipo_cambio": "retraso",
                    **payload,
                })
        elif existente and existente.get("estado") == "activa":
            pb.update("disrupciones", existente["id"], {"estado": "resuelta"})
            resueltos += 1

    resumen = {
        "vuelos_evaluados": evaluados,
        "riesgo_alto": altos,
        "disrupciones_actualizadas": actualizados,
        "disrupciones_resueltas": resueltos,
    }
    print(f"[DISRUPCION-SIM] {resumen}")
    return resumen
