"""
AeroTrack Travel — ETL dims: BTS/FAA (aerotrack-travel-dims) -> ClickHouse
=============================================================================
DAG `aerotrack_travel_etl_dims` (spec: docs/aerotrack-travel-dashboards-spec.md
sección 1). Alimenta las 3 tablas ClickHouse `agg_otp_aerolinea_mes`,
`agg_causas_retraso_mes`, `agg_otp_dia_semana` con granularidad ruta +
aerolínea + mes/día de semana.

Corrección sobre el pedido original (documentada al reportar el resultado
de esta corrida, ver docs/etl-clickhouse-auditoria.md sección 3.4): NO
existen columnas planas `Origin`/`Dest`/`UniqueCarrier`/`Month` en
`fact_vuelo.parquet` — es un esquema en estrella con foreign keys
(`fk_aerolinea`, `fk_ruta`, `fk_tiempo`, `fk_clasificacion_retraso`,
`fk_retraso_causa`), hay que unir contra `dim_aerolinea`/`dim_ruta`/
`dim_tiempo`/`dim_clasificacion_retraso`/`dim_retraso_causa`. El resultado
final (periodo/aerolínea/ruta) es exactamente el que se pidió, solo cambia
el camino para llegar a él.

`retraso_promedio_min` no tiene una columna `ArrDelay` cruda disponible en
ningún Parquet de dims — se aproxima como el promedio de la suma de las 5
causas de retraso (`CarrierDelay+WeatherDelay+NASDelay+SecurityDelay+
LateAircraftDelay`) por vuelo, que es 0 para vuelos a tiempo y el desglose
real de BTS para vuelos con retraso ≥15min (la única fuente de minutos de
retraso que existe en el dataset).
"""

from __future__ import annotations

import datetime

import clickhouse_client as ch
import config
import minio_dims_reader
import pandas as pd

COLUMNAS_FACT = ["fk_aerolinea", "fk_ruta", "fk_tiempo", "fk_clasificacion_retraso", "fk_retraso_causa"]
CAUSAS_COLUMNAS = ["CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay"]
CAUSAS_MAPA = {
    "CarrierDelay": "carrier",
    "WeatherDelay": "weather",
    "NASDelay": "nas",
    "SecurityDelay": "security",
    "LateAircraftDelay": "late_aircraft",
}

ARCHIVOS = [
    "fact_vuelo",
    "dim_tiempo",
    "dim_aerolinea",
    "dim_ruta",
    "dim_clasificacion_retraso",
    "dim_retraso_causa",
]


def _nombre_archivo(base: str, marca: str) -> str:
    return f"{base}_{marca}.parquet"


def extraer() -> dict:
    """Lee fact_vuelo (solo las FK necesarias, no las ~15 columnas de
    detalle del vuelo que no se usan acá) + las 5 dims que hacen falta para
    resolver periodo/aerolínea/ruta/clasificación de retraso. Escribe cada
    una como Parquet en `Parquet/crudo/`."""
    marca = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H%M%S")

    fact = minio_dims_reader.read_parquet("fact_vuelo", COLUMNAS_FACT)
    dim_tiempo = minio_dims_reader.read_parquet("dim_tiempo", ["pk_tiempo", "Year", "Month", "DayOfWeek"])
    dim_aerolinea = minio_dims_reader.read_parquet("dim_aerolinea", ["pk_aerolinea", "IATA_CODE_Reporting_Airline"])
    dim_ruta = minio_dims_reader.read_parquet("dim_ruta", ["pk_ruta", "OriginCode", "DestCode"])
    dim_clasif = minio_dims_reader.read_parquet("dim_clasificacion_retraso", ["pk_clasificacion", "ArrDel15"])
    dim_causa = minio_dims_reader.read_parquet("dim_retraso_causa", ["pk_retraso_causa"] + CAUSAS_COLUMNAS)

    dataframes = {
        "fact_vuelo": fact, "dim_tiempo": dim_tiempo, "dim_aerolinea": dim_aerolinea,
        "dim_ruta": dim_ruta, "dim_clasificacion_retraso": dim_clasif, "dim_retraso_causa": dim_causa,
    }
    for base, df in dataframes.items():
        ch.escribir_parquet(df, _nombre_archivo(base, marca), config.PARQUET_CRUDO)

    print(f"[extraer] marca={marca} fact_vuelo={len(fact)} filas")
    return {"marca": marca, "filas_fact_vuelo": len(fact)}


def _aerolinea_nombre_por_codigo() -> dict[str, str]:
    """Solo las 5 aerolíneas activas de la app tienen nombre legible
    (`aerolineas` en PocketBase) — el resto de los ~1000 carriers
    históricos de BTS/FAA quedan con el código como nombre, no hay fuente
    de nombres completos para ellos en este proyecto."""
    import pocketbase_client

    aerolineas = pocketbase_client.list_all("aerolineas")
    return {a["codigo_iata"]: a["nombre"] for a in aerolineas}


def transformar(extraido: dict) -> dict:
    marca = extraido["marca"]

    dataframes = {}
    for base in ARCHIVOS:
        nombre = _nombre_archivo(base, marca)
        dataframes[base] = pd.read_parquet(config.PARQUET_CRUDO / nombre)
        ch.mover_parquet(nombre, config.PARQUET_CRUDO, config.PARQUET_PROCESANDO)

    df = dataframes["fact_vuelo"]
    df = df.merge(dataframes["dim_tiempo"], left_on="fk_tiempo", right_on="pk_tiempo", how="left")
    df = df.merge(dataframes["dim_aerolinea"], left_on="fk_aerolinea", right_on="pk_aerolinea", how="left")
    df = df.merge(dataframes["dim_ruta"], left_on="fk_ruta", right_on="pk_ruta", how="left")
    df = df.merge(dataframes["dim_clasificacion_retraso"], left_on="fk_clasificacion_retraso", right_on="pk_clasificacion", how="left")
    df = df.merge(dataframes["dim_retraso_causa"], left_on="fk_retraso_causa", right_on="pk_retraso_causa", how="left")

    df = df.rename(columns={"IATA_CODE_Reporting_Airline": "aerolinea_codigo", "OriginCode": "origen", "DestCode": "destino"})
    df["periodo"] = pd.to_datetime(
        df["Year"].astype("Int64").astype(str) + "-" + df["Month"].astype("Int64").astype(str).str.zfill(2) + "-01",
        errors="coerce",
    ).dt.date
    df["a_tiempo"] = (df["ArrDel15"] == 0).astype("Int64")
    df["retraso_causas_min"] = df[CAUSAS_COLUMNAS].sum(axis=1)

    nombres_por_codigo = _aerolinea_nombre_por_codigo()

    # ── agg_otp_aerolinea_mes ────────────────────────────────────────
    otp_mes = df.groupby(["periodo", "aerolinea_codigo", "origen", "destino"]).agg(
        total_vuelos=("a_tiempo", "size"),
        vuelos_a_tiempo=("a_tiempo", "sum"),
        retraso_promedio_min=("retraso_causas_min", "mean"),
    ).reset_index()
    otp_mes["otp_porcentaje"] = (otp_mes["vuelos_a_tiempo"] / otp_mes["total_vuelos"] * 100).round(2)
    otp_mes["retraso_promedio_min"] = otp_mes["retraso_promedio_min"].round(2)
    otp_mes["aerolinea_nombre"] = otp_mes["aerolinea_codigo"].map(nombres_por_codigo).fillna(otp_mes["aerolinea_codigo"])
    otp_mes["total_vuelos"] = otp_mes["total_vuelos"].astype("uint32")
    otp_mes["vuelos_a_tiempo"] = otp_mes["vuelos_a_tiempo"].astype("uint32")
    otp_mes = otp_mes[["periodo", "aerolinea_codigo", "aerolinea_nombre", "origen", "destino", "total_vuelos", "vuelos_a_tiempo", "otp_porcentaje", "retraso_promedio_min"]]

    # ── agg_causas_retraso_mes ───────────────────────────────────────
    partes = []
    for columna, causa in CAUSAS_MAPA.items():
        sub = df[df[columna] > 0].groupby(["periodo", "origen", "destino"]).size().reset_index(name="total_casos")
        sub["causa"] = causa
        partes.append(sub)
    causas_mes = pd.concat(partes, ignore_index=True)
    totales = causas_mes.groupby(["periodo", "origen", "destino"])["total_casos"].transform("sum")
    causas_mes["porcentaje_del_total"] = (causas_mes["total_casos"] / totales * 100).round(2)
    causas_mes["total_casos"] = causas_mes["total_casos"].astype("uint32")
    causas_mes = causas_mes[["periodo", "origen", "destino", "causa", "total_casos", "porcentaje_del_total"]]

    # ── agg_otp_dia_semana ───────────────────────────────────────────
    dia_semana = df.groupby(["origen", "destino", "DayOfWeek"]).agg(
        total_vuelos=("a_tiempo", "size"),
        vuelos_a_tiempo=("a_tiempo", "sum"),
    ).reset_index()
    dia_semana["otp_porcentaje"] = (dia_semana["vuelos_a_tiempo"] / dia_semana["total_vuelos"] * 100).round(2)
    dia_semana = dia_semana.rename(columns={"DayOfWeek": "dia_semana"})
    dia_semana["dia_semana"] = dia_semana["dia_semana"].astype("uint8")
    dia_semana["total_vuelos"] = dia_semana["total_vuelos"].astype("uint32")
    dia_semana["vuelos_a_tiempo"] = dia_semana["vuelos_a_tiempo"].astype("uint32")
    dia_semana = dia_semana[["origen", "destino", "dia_semana", "total_vuelos", "vuelos_a_tiempo", "otp_porcentaje"]]

    salidas = {
        "agg_otp_aerolinea_mes": otp_mes,
        "agg_causas_retraso_mes": causas_mes,
        "agg_otp_dia_semana": dia_semana,
    }
    for tabla, resultado in salidas.items():
        ch.escribir_parquet(resultado, _nombre_archivo(tabla, marca), config.PARQUET_PROCESANDO)
        print(f"[transformar] {tabla}: {len(resultado)} filas")

    # Las 6 copias crudas (fact_vuelo + 5 dims) ya cumplieron su función —
    # el dato original vive permanentemente en `aerotrack-travel-dims`, no
    # hay valor en conservar una copia scratch por corrida. Sin este borrado
    # se acumulan ~16MB/corrida en `procesando/` sin ningún propósito (la
    # carpeta nunca las movería a `terminado/` porque `cargar()` solo mueve
    # los 3 archivos de salida).
    for base in ARCHIVOS:
        (config.PARQUET_PROCESANDO / _nombre_archivo(base, marca)).unlink(missing_ok=True)

    return {"marca": marca, "filas": {t: len(r) for t, r in salidas.items()}}


def cargar(transformado: dict) -> dict:
    marca = transformado["marca"]
    tablas = ["agg_otp_aerolinea_mes", "agg_causas_retraso_mes", "agg_otp_dia_semana"]

    resultado: dict[str, int] = {}
    for tabla in tablas:
        nombre = _nombre_archivo(tabla, marca)
        df = pd.read_parquet(config.PARQUET_PROCESANDO / nombre)
        insertadas = ch.insertar_df(f"aerotrack_travel.{tabla}", df)
        ch.mover_parquet(nombre, config.PARQUET_PROCESANDO, config.PARQUET_TERMINADO)
        resultado[tabla] = insertadas
        print(f"[cargar] {tabla}: {insertadas} filas insertadas en ClickHouse")

    return resultado
