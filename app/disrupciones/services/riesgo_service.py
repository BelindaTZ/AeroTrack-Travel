"""RF-DIS-002 (CU-O39) — simulador estadístico de riesgo de disrupción.

Equivalente "delgado" de `dags/disrupciones_tasks.py::estimar_riesgo_disrupcion`
(paso 6 del plan de migración): la lógica se movió a la app porque
`disrupciones` ya vive en MinIO y solo la app tiene acceso a
`DisrupcionesRepository`/`minio_operational_client` — el DAG
(`dag_estimar_riesgo_disrupcion.py`) pasa a ser un disparador delgado que
llama a `POST /internal/disrupciones/estimar-riesgo`, mismo patrón que
`api_estado_vuelo_service.py`/`monitor_correo_service.py`.

Principio E2 (deduplicación entre fuentes): nunca crea una segunda fila
para el mismo vuelo — actualiza la disrupción existente de esta misma
fuente (`fuente_deteccion="simulador_estadistico"`) si ya existe.
"""

import datetime

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.shared import minio_operational_client as moc
from app.shared.minio_dims_reader import leer_parquet
from app.shared.pocketbase_client import get_pocketbase_client

UMBRAL_RIESGO_PCT_DEFAULT = 20.0
CAUSAS = ["carrierdelay", "weatherdelay", "nasdelay", "securitydelay", "lateaircraftdelay"]
CAUSAS_LEGIBLES = {
    "carrierdelay": "la propia aerolínea",
    "weatherdelay": "condiciones climáticas",
    "nasdelay": "el sistema nacional de espacio aéreo",
    "securitydelay": "procesos de seguridad",
    "lateaircraftdelay": "la llegada tardía de la aeronave anterior",
}


async def _otp_por_aerolinea() -> dict[str, float]:
    """Promedio de otp_pct de los últimos 12 registros mensuales disponibles
    por aerolínea (histórico BTS/FAA, agg_otp_aerolinea_mes)."""
    filas = await leer_parquet("agg_otp_aerolinea_mes", ["carrier", "year", "month", "otp_pct"])
    por_carrier: dict[str, list[dict]] = {}
    for fila in filas:
        por_carrier.setdefault(fila["carrier"], []).append(fila)

    promedios: dict[str, float] = {}
    for carrier, registros in por_carrier.items():
        registros.sort(key=lambda r: (r["year"], r["month"]))
        ultimos = registros[-12:]
        promedios[carrier] = round(sum(r["otp_pct"] for r in ultimos) / len(ultimos), 2)
    return promedios


async def _causa_dominante_por_aerolinea() -> dict[str, str]:
    """Causa de retraso con mayor suma acumulada por aerolínea (agg_causas_retraso_mes)."""
    filas = await leer_parquet("agg_causas_retraso_mes", ["carrier"] + CAUSAS)
    if not filas:
        return {}
    disponibles = [c for c in CAUSAS if c in filas[0]]
    if not disponibles:
        return {}

    sumas: dict[str, dict[str, float]] = {}
    for fila in filas:
        acumulado = sumas.setdefault(fila["carrier"], {c: 0.0 for c in disponibles})
        for c in disponibles:
            acumulado[c] += fila.get(c) or 0

    return {carrier: max(valores, key=valores.get) for carrier, valores in sumas.items()}


async def _vuelos_programados_lejanos(limite_lejania: datetime.datetime) -> list[dict]:
    client = get_pocketbase_client()
    resultado = await client.list_records(
        "vuelos_catalogo", {"filter": 'estado="programado"', "perPage": 500}
    )
    return [
        v for v in resultado["items"]
        if _fecha_salida(v) is not None and _fecha_salida(v) > limite_lejania
    ]


def _fecha_salida(vuelo: dict) -> datetime.datetime | None:
    try:
        return datetime.datetime.strptime(vuelo["fecha_salida"][:10], "%Y-%m-%d")
    except (ValueError, KeyError):
        return None


async def riesgo_estimado_por_aerolinea() -> dict[str, float]:
    """IS-11 (auditoría de informes simples, sesión 2026-08-01) — expone el
    mismo cálculo de `estimar_riesgo_disrupcion` (100 - OTP histórico) para
    que el dashboard de vuelos activos pueda mostrar un nivel de riesgo por
    vuelo sin duplicar la lectura del parquet ni esperar a que corra el DAG:
    acá se calcula en vivo, de solo lectura, sin crear ninguna `disrupcion`.
    Devuelve {codigo_iata: riesgo_pct}."""
    otp = await _otp_por_aerolinea()
    return {iata: round(100 - pct, 2) for iata, pct in otp.items()}


async def estimar_riesgo_disrupcion() -> dict:
    """CU-O39. Recorre vuelos_catalogo 'programados' fuera del umbral de
    API real y crea/actualiza una fila en disrupciones cuando el riesgo
    histórico de la aerolínea supera el umbral configurado."""
    repo = DisrupcionesRepository()
    config_umbral_horas = await repo.config("disrupciones.umbral_api_real_horas")
    umbral_horas = int(config_umbral_horas["valor"]) if config_umbral_horas else 72
    config_umbral_riesgo = await repo.config("simulador_disrupciones.umbral_riesgo_pct")
    umbral_riesgo = float(config_umbral_riesgo["valor"]) if config_umbral_riesgo else UMBRAL_RIESGO_PCT_DEFAULT

    otp = await _otp_por_aerolinea()
    causa_dominante = await _causa_dominante_por_aerolinea()

    limite_lejania = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(hours=umbral_horas)
    vuelos = await _vuelos_programados_lejanos(limite_lejania)

    client = get_pocketbase_client()
    aerolineas_cache: dict[str, dict] = {}

    # Índice (vuelo_id, fuente_deteccion) -> disrupción, una sola pasada —
    # evitar re-listar todo `disrupciones` por cada vuelo del bucle (E2:
    # nunca duplicar fila por vuelo+fuente, sin importar el `estado` actual,
    # a diferencia de `disrupciones_de_vuelo_y_tipo` que solo mira activas).
    todas = await moc.listar_todos("disrupciones")
    indice = {(d.get("vuelo_id"), d.get("fuente_deteccion")): d for d in todas}

    evaluados = altos = actualizados = resueltos = 0

    for v in vuelos:
        aerolinea_id = v.get("aerolinea_id")
        if aerolinea_id not in aerolineas_cache:
            try:
                aerolineas_cache[aerolinea_id] = await client.get_record("aerolineas", aerolinea_id)
            except Exception:
                aerolineas_cache[aerolinea_id] = None
        aerolinea = aerolineas_cache[aerolinea_id]
        if not aerolinea:
            continue
        iata = aerolinea["codigo_iata"]
        otp_pct = otp.get(iata)
        if otp_pct is None:
            continue

        evaluados += 1
        riesgo = round(100 - otp_pct, 2)
        existente = indice.get((v["id"], "simulador_estadistico"))

        ahora_iso = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")
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
                "fecha_deteccion": ahora_iso,
            }
            if existente:
                await repo.actualizar_disrupcion(existente["id"], payload)
                actualizados += 1
            else:
                await repo.crear_disrupcion(
                    {
                        "vuelo_id": v["id"],
                        "fuente_deteccion": "simulador_estadistico",
                        "tipo_cambio": "retraso",
                        **payload,
                    }
                )
        elif existente and existente.get("estado") == "activa":
            await repo.actualizar_disrupcion(existente["id"], {"estado": "resuelta"})
            resueltos += 1

    resumen = {
        "vuelos_evaluados": evaluados,
        "riesgo_alto": altos,
        "disrupciones_actualizadas": actualizados,
        "disrupciones_resueltas": resueltos,
    }
    return resumen
