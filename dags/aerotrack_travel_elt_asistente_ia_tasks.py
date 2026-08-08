"""
AeroTrack Travel — ELT asistente IA: MinIO operacional (vía /internal/analitica)
-> ClickHouse
================================================================================
DAG `aerotrack_travel_elt_asistente_ia`. Alimenta `agg_uso_asistente_ia`
(tabla estratégica nueva, Fase B.3 — soporta DS-03) desde
`mensajes_ia`/`conversaciones_ia`, vía los endpoints internos ya existentes
`/internal/analitica/mensajes-ia` y `/internal/analitica/conversaciones-ia`
(no hizo falta agregar endpoints nuevos, `router_interno_analitica.py` ya
los tenía desde el ETL comercial original).

Gaps reales de esquema, no de código (confirmado contra
`app/asistente_ia/repositories/asistente_repo.py` — mismos gaps que ya
documentó `app/dashboards/services/asistente_ia_service.py` para DB-11):
- `mensajes_ia` NO tiene campo `categoria` ni `tipo` (informativa/
  transaccional) — la tabla se agrega solo por `periodo`, sin la dimensión
  `categoria` que pedía el spec original (ORDER BY (periodo, categoria));
  no existe ninguna señal real para poblarla sin inventar una taxonomía.
- `calificacion` SÍ existe, pero es binaria (`"arriba"`/`"abajo"`, ver
  `router_conversacion.py::calificar`), no un rating 1-5 como sugiere el
  nombre `calificacion_promedio` de `agg_satisfaccion_soporte` (soporte,
  tabla distinta). Por eso acá se expone `pct_calificacion_positiva`
  (arriba / calificadas × 100) + `total_calificadas` como denominador de
  contexto, en vez de un `calificacion_promedio` que fingiría una escala
  que no existe en el dato real.

Acoplamiento a vigilar: `_MARCADORES_SIN_RESPUESTA` está duplicado acá
desde `app/asistente_ia/services/asistente_service.py` porque el contenedor
de Airflow solo monta `dags/`, no `app/` — si el texto canónico de fallback
cambia en la app, hay que actualizarlo también acá o `temas_sin_respuesta`
queda desincronizado. Mismo patrón de límite Airflow/app que ya describe
`aerotrack_travel_etl_comercial_tasks.py` para las decisiones de atribución.
"""

from __future__ import annotations

import datetime

import clickhouse_client as ch
import config
import pandas as pd
import requests

ARCHIVOS = ["mensajes-ia", "conversaciones-ia"]

# Duplicado desde app/asistente_ia/services/asistente_service.py — ver nota
# de acoplamiento en el docstring del módulo.
_MARCADORES_SIN_RESPUESTA = (
    "No puedo generar una respuesta abierta en este momento — nuestro asistente de IA no está disponible. "
    "¿Quieres que escalemos tu consulta a un agente humano?",
    "No tengo un dato verificado en el sistema para responder eso con seguridad todavía. "
    "¿Quieres que escalemos tu consulta a un agente humano?",
    "fuera de los temas",
)


def _nombre_archivo(base: str, marca: str) -> str:
    return f"{base}_{marca}.parquet"


def _obtener(endpoint: str) -> pd.DataFrame:
    resp = requests.get(f"{config.APP_TRAVEL_URL}/internal/analitica/{endpoint}", timeout=60)
    resp.raise_for_status()
    return pd.DataFrame(resp.json())


def extraer() -> dict:
    marca = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H%M%S")
    conteos = {}
    for base in ARCHIVOS:
        df = _obtener(base)
        ch.escribir_parquet(df, _nombre_archivo(base, marca), config.PARQUET_E)
        conteos[base] = len(df)
    print(f"[extraer] marca={marca} {conteos}")
    return {"marca": marca, "conteos": conteos}


def _mes_a_periodo(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, errors="coerce").dt.to_period("M").dt.to_timestamp().dt.date


def _contar_temas_sin_respuesta(mensajes: pd.DataFrame) -> pd.DataFrame:
    """Mismo criterio que `asistente_ia_service.py` (RF-IA-T02): un mensaje
    de `usuario` sin respuesta verificable es aquel seguido, dentro de la
    MISMA conversación, por un mensaje de `asistente` que coincide con
    alguno de los mensajes canónicos de fallback. A diferencia del service
    original (que asume la lista ya viene en orden cronológico por índice),
    acá se ordena explícitamente por `conversacion_id`+`fecha` antes de
    comparar con la fila siguiente — más robusto si el orden de listado de
    MinIO no es cronológico."""
    if mensajes.empty:
        return pd.DataFrame(columns=["periodo", "tema"])

    m = mensajes.sort_values(["conversacion_id", "fecha"]).reset_index(drop=True)
    siguiente_rol = m["rol"].shift(-1)
    siguiente_contenido = m["contenido"].shift(-1)
    siguiente_conversacion = m["conversacion_id"].shift(-1)

    es_fallback = siguiente_contenido.fillna("").apply(
        lambda c: any(marcador in c for marcador in _MARCADORES_SIN_RESPUESTA)
    )
    mascara = (
        (m["rol"] == "usuario")
        & (siguiente_rol == "asistente")
        & (siguiente_conversacion == m["conversacion_id"])
        & es_fallback
    )
    sin_respuesta = m[mascara].copy()
    sin_respuesta["periodo"] = _mes_a_periodo(sin_respuesta["fecha"])
    return sin_respuesta[["periodo", "contenido"]].rename(columns={"contenido": "tema"})


def transformar(extraido: dict) -> dict:
    marca = extraido["marca"]

    dataframes = {}
    for base in ARCHIVOS:
        nombre = _nombre_archivo(base, marca)
        dataframes[base] = pd.read_parquet(config.PARQUET_E / nombre)
        ch.mover_parquet(nombre, config.PARQUET_E, config.PARQUET_T)

    mensajes = dataframes["mensajes-ia"]
    conversaciones = dataframes["conversaciones-ia"]

    columnas = [
        "periodo", "total_conversaciones", "total_consultas",
        "total_calificadas", "pct_calificacion_positiva", "temas_sin_respuesta",
    ]

    if conversaciones.empty and mensajes.empty:
        resultado = pd.DataFrame(columns=columnas)
    else:
        # total_conversaciones por mes de inicio
        conv_mes = pd.DataFrame(columns=["periodo", "total_conversaciones"])
        if not conversaciones.empty:
            conversaciones["periodo"] = _mes_a_periodo(conversaciones["fecha_inicio"])
            conv_mes = conversaciones.groupby("periodo").size().reset_index(name="total_conversaciones")

        # total_consultas (mensajes de rol usuario) por mes de la consulta
        consultas_mes = pd.DataFrame(columns=["periodo", "total_consultas"])
        calificadas_mes = pd.DataFrame(columns=["periodo", "total_calificadas", "pct_calificacion_positiva"])
        temas_mes = pd.DataFrame(columns=["periodo", "temas_sin_respuesta"])
        if not mensajes.empty:
            mensajes["periodo"] = _mes_a_periodo(mensajes["fecha"])
            consultas = mensajes[mensajes["rol"] == "usuario"]
            if not consultas.empty:
                consultas_mes = consultas.groupby("periodo").size().reset_index(name="total_consultas")

            if "calificacion" in mensajes.columns:
                calificados = mensajes[mensajes["calificacion"].isin(["arriba", "abajo"])]
                if not calificados.empty:
                    calificadas_mes = calificados.groupby("periodo").agg(
                        total_calificadas=("calificacion", "size"),
                        positivas=("calificacion", lambda s: (s == "arriba").sum()),
                    ).reset_index()
                    calificadas_mes["pct_calificacion_positiva"] = (
                        calificadas_mes["positivas"] / calificadas_mes["total_calificadas"] * 100
                    ).round(2)
                    calificadas_mes = calificadas_mes[["periodo", "total_calificadas", "pct_calificacion_positiva"]]

            sin_respuesta = _contar_temas_sin_respuesta(mensajes)
            if not sin_respuesta.empty:
                temas_mes = sin_respuesta.groupby("periodo")["tema"].nunique().reset_index(name="temas_sin_respuesta")

        resultado = conv_mes.merge(consultas_mes, on="periodo", how="outer")
        resultado = resultado.merge(calificadas_mes, on="periodo", how="outer")
        resultado = resultado.merge(temas_mes, on="periodo", how="outer")
        resultado = resultado.dropna(subset=["periodo"])
        for col in ["total_conversaciones", "total_consultas", "total_calificadas", "temas_sin_respuesta"]:
            resultado[col] = resultado[col].fillna(0).astype("uint32")
        resultado["pct_calificacion_positiva"] = resultado["pct_calificacion_positiva"].fillna(0.0)
        resultado = resultado[columnas]

    ch.escribir_parquet(resultado, _nombre_archivo("agg_uso_asistente_ia", marca), config.PARQUET_T)
    print(f"[transformar] agg_uso_asistente_ia: {len(resultado)} filas")

    for base in ARCHIVOS:
        (config.PARQUET_T / _nombre_archivo(base, marca)).unlink(missing_ok=True)

    return {"marca": marca, "filas": {"agg_uso_asistente_ia": len(resultado)}}


def cargar(transformado: dict) -> dict:
    marca = transformado["marca"]
    nombre = _nombre_archivo("agg_uso_asistente_ia", marca)
    df = pd.read_parquet(config.PARQUET_T / nombre)
    insertadas = ch.insertar_df("aerotrack_travel.agg_uso_asistente_ia", df)
    ch.mover_parquet(nombre, config.PARQUET_T, config.PARQUET_L)
    print(f"[cargar] agg_uso_asistente_ia: {insertadas} filas insertadas en ClickHouse")
    return {"agg_uso_asistente_ia": insertadas}
