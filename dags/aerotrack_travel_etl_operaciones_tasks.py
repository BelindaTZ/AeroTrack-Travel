"""
AeroTrack Travel — ETL operaciones: MinIO operacional (vía /internal/analitica)
-> ClickHouse
==================================================================================
DAG `aerotrack_travel_etl_operaciones`. Alimenta `agg_disrupciones_aerolinea_ruta`
y `agg_satisfaccion_soporte`.

Gaps reales de datos/esquema encontrados (documentados acá, no son bugs de
este código — la forma correcta de resolverlos es sembrar mejores datos
demo en B.6, o en un caso agregar un campo nuevo si hiciera falta de
verdad para Fase C):

- `notificaciones.disrupcion_id` SÍ existe en el esquema real (lo setea
  `procesar_disrupcion` en el flujo de producción) pero HOY 0 de las 4
  notificaciones en la base lo tienen poblado — son artefactos de test de
  sesiones anteriores, creados con un helper de prueba que no lo setea.
  Con los datos actuales, `agg_disrupciones_aerolinea_ruta` va a salir
  vacía — el join está bien escrito, el dato vinculado no existe todavía.
- No existe ningún campo de "con_accion_pasajero" en `notificaciones` ni
  `disrupciones` — se aproxima como: la reserva de la notificación pasó a
  `modificada`/`cancelada` DESPUÉS de que se envió la notificación.
- Ni `mensajes_ia` ni `casos_escalados` tienen un campo `categoria` (el
  pedido original lo asumía) — se agrupa todo bajo `categoria='general'`.
  Si más adelante se quiere una categorización real, hace falta agregar el
  campo al esquema primero, no es algo que se pueda inventar acá.
- `tasa_escalacion` conecta dos sistemas sin vínculo directo entre sí
  (mensajes del asistente IA vs. casos escalados de centro de ayuda) — se
  aproxima como casos_escalados del mes / consultas del mes, mismo criterio
  de "conflate" que ya sugiere el propio spec para DB-09.
- `calificacion` de un mensaje es "arriba"/"abajo" (no numérica) —
  `calificacion_promedio` es el % de calificaciones "arriba" sobre el
  total de mensajes calificados.
"""

from __future__ import annotations

import datetime

import clickhouse_client as ch
import config
import pandas as pd
import pocketbase_client
import requests

ARCHIVOS = ["disrupciones", "notificaciones", "casos-escalados", "mensajes-ia"]


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
        ch.escribir_parquet(df, _nombre_archivo(base, marca), config.PARQUET_CRUDO)
        conteos[base] = len(df)

    # vuelos_catalogo/aerolineas son PocketBase STAGING/CONFIG, no
    # OPERACIONAL — leerlas directo vía pocketbase_client (mismo patrón que
    # catalogo_minio_publisher.py) no rompe la regla de MinIO operacional.
    vuelos = pd.DataFrame(pocketbase_client.list_all("vuelos_catalogo"))
    aerolineas = pd.DataFrame(pocketbase_client.list_all("aerolineas"))
    ch.escribir_parquet(vuelos, _nombre_archivo("vuelos_catalogo", marca), config.PARQUET_CRUDO)
    ch.escribir_parquet(aerolineas, _nombre_archivo("aerolineas", marca), config.PARQUET_CRUDO)
    conteos["vuelos_catalogo"] = len(vuelos)
    conteos["aerolineas"] = len(aerolineas)

    print(f"[extraer] marca={marca} {conteos}")
    return {"marca": marca, "conteos": conteos}


def _mes_a_periodo(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, errors="coerce").dt.to_period("M").dt.to_timestamp().dt.date


def transformar(extraido: dict) -> dict:
    marca = extraido["marca"]
    archivos_todos = ARCHIVOS + ["vuelos_catalogo", "aerolineas"]

    dataframes = {}
    for base in archivos_todos:
        nombre = _nombre_archivo(base, marca)
        dataframes[base] = pd.read_parquet(config.PARQUET_CRUDO / nombre)
        ch.mover_parquet(nombre, config.PARQUET_CRUDO, config.PARQUET_PROCESANDO)

    notificaciones = dataframes["notificaciones"]
    vuelos = dataframes["vuelos_catalogo"]
    aerolineas = dataframes["aerolineas"]
    casos = dataframes["casos-escalados"]
    mensajes = dataframes["mensajes-ia"]

    # ── agg_disrupciones_aerolinea_ruta ──────────────────────────────
    columnas_disr = [
        "periodo", "aerolinea_codigo", "aerolinea_nombre", "origen", "destino",
        "total_notificaciones", "exitosas", "fallidas", "con_accion_pasajero",
        "tasa_efectividad", "otp_benchmark_bts",
    ]
    con_disrupcion = notificaciones[notificaciones.get("disrupcion_id", pd.Series(dtype=object)).fillna("") != ""] \
        if "disrupcion_id" in notificaciones.columns else notificaciones.iloc[0:0]

    if not con_disrupcion.empty and not vuelos.empty:
        # notificacion -> reserva -> reserva_items (tipo_producto=vuelo) ->
        # vuelo -> aerolinea/ruta. Se resuelve el vuelo vía `reserva_items`,
        # NO vía el campo legado `reservas.vuelo_id` (dual-write que ya no
        # se escribe para reservas armadas por fuera del flujo original de
        # Vuelos, ver `reservas_repo.py`) — con datos reales encontramos que
        # ese campo puede venir vacío aunque la reserva sí tenga un ítem de
        # vuelo real en `reserva_items`.
        resp = requests.get(f"{config.APP_TRAVEL_URL}/internal/analitica/reservas", timeout=60)
        resp.raise_for_status()
        reservas = pd.DataFrame(resp.json())
        resp_items = requests.get(f"{config.APP_TRAVEL_URL}/internal/analitica/reserva-items", timeout=60)
        resp_items.raise_for_status()
        items = pd.DataFrame(resp_items.json())
        vuelo_por_reserva = (
            items[items["tipo_producto"] == "vuelo"][["reserva_id", "vuelo_id"]].drop_duplicates("reserva_id")
            if not items.empty else pd.DataFrame(columns=["reserva_id", "vuelo_id"])
        )

        notif_r = con_disrupcion.merge(
            reservas[["id", "estado", "updated"]].rename(columns={"id": "reserva_id", "updated": "reserva_updated"}),
            on="reserva_id", how="left",
        )
        notif_r = notif_r.merge(vuelo_por_reserva, on="reserva_id", how="left")
        notif_rv = notif_r.merge(
            vuelos[["id", "aerolinea_id", "origen_codigo", "destino_codigo"]].rename(columns={"id": "vuelo_id"}),
            on="vuelo_id", how="left",
        )
        notif_rva = notif_rv.merge(
            aerolineas[["id", "codigo_iata", "nombre"]].rename(columns={"id": "aerolinea_id"}),
            on="aerolinea_id", how="left",
        )
        notif_rva["periodo"] = _mes_a_periodo(notif_rva["created"])
        notif_rva["es_exitosa"] = notif_rva["estado_envio"] == "enviado"
        notif_rva["es_fallida"] = notif_rva["estado_envio"].isin(["fallido", "fallido_definitivo"])
        # proxy de "con acción del pasajero": la reserva se modificó o
        # canceló después del envío de la notificación (no hay campo directo).
        notif_rva["con_accion"] = (
            notif_rva["estado"].isin(["modificada", "cancelada"])
            & (notif_rva["reserva_updated"] > notif_rva["created"])
        )

        disrup = notif_rva.groupby(["periodo", "codigo_iata", "nombre", "origen_codigo", "destino_codigo"]).agg(
            total_notificaciones=("id", "size"),
            exitosas=("es_exitosa", "sum"),
            fallidas=("es_fallida", "sum"),
            con_accion_pasajero=("con_accion", "sum"),
        ).reset_index()
        disrup = disrup.rename(columns={
            "codigo_iata": "aerolinea_codigo", "nombre": "aerolinea_nombre",
            "origen_codigo": "origen", "destino_codigo": "destino",
        })
        disrup["tasa_efectividad"] = (
            disrup["con_accion_pasajero"] / disrup["exitosas"].replace(0, pd.NA) * 100
        ).fillna(0).round(2)

        # benchmark OTP real (agg_otp_aerolinea_mes ya cargada por
        # aerotrack_travel_etl_dims) — mismo período/aerolínea/ruta.
        otp = pd.DataFrame(ch.ejecutar_query(
            "SELECT periodo, aerolinea_codigo, origen, destino, otp_porcentaje FROM aerotrack_travel.agg_otp_aerolinea_mes"
        ), columns=["periodo", "aerolinea_codigo", "origen", "destino", "otp_porcentaje"])
        if not otp.empty:
            disrup = disrup.merge(otp, on=["periodo", "aerolinea_codigo", "origen", "destino"], how="left")
            disrup = disrup.rename(columns={"otp_porcentaje": "otp_benchmark_bts"})
        else:
            disrup["otp_benchmark_bts"] = pd.NA
        disrup["otp_benchmark_bts"] = disrup["otp_benchmark_bts"].fillna(0).astype(float).round(2)

        for col in ["total_notificaciones", "exitosas", "fallidas", "con_accion_pasajero"]:
            disrup[col] = disrup[col].astype("uint32")
        disrup = disrup[columnas_disr]
    else:
        disrup = pd.DataFrame(columns=columnas_disr)

    # ── agg_satisfaccion_soporte ─────────────────────────────────────
    columnas_sat = [
        "periodo", "categoria", "total_consultas", "calificacion_promedio",
        "tasa_escalacion", "tiempo_promedio_resolucion_horas",
    ]
    consultas_por_mes = pd.DataFrame(columns=["periodo", "total_consultas"])
    calif_por_mes = pd.DataFrame(columns=["periodo", "calificacion_promedio"])
    if not mensajes.empty:
        consultas = mensajes[mensajes["rol"] == "usuario"].copy()
        consultas["periodo"] = _mes_a_periodo(consultas["fecha"])
        consultas_por_mes = consultas.groupby("periodo").size().reset_index(name="total_consultas")

        calificados = mensajes[mensajes.get("calificacion", pd.Series(dtype=object)).notna()].copy() \
            if "calificacion" in mensajes.columns else mensajes.iloc[0:0]
        if not calificados.empty:
            calificados["periodo"] = _mes_a_periodo(calificados["fecha"])
            calif_por_mes = calificados.groupby("periodo")["calificacion"].apply(
                lambda s: round((s == "arriba").sum() / len(s) * 100, 2)
            ).reset_index(name="calificacion_promedio")

    escalados_por_mes = pd.DataFrame(columns=["periodo", "casos_escalados"])
    resolucion_por_mes = pd.DataFrame(columns=["periodo", "tiempo_promedio_resolucion_horas"])
    if not casos.empty:
        casos = casos.copy()
        casos["periodo"] = _mes_a_periodo(casos["fecha_creacion"])
        escalados_por_mes = casos.groupby("periodo").size().reset_index(name="casos_escalados")

        resueltos = casos[casos.get("fecha_resolucion", pd.Series(dtype=object)).notna()].copy() \
            if "fecha_resolucion" in casos.columns else casos.iloc[0:0]
        if not resueltos.empty:
            horas = (
                pd.to_datetime(resueltos["fecha_resolucion"]) - pd.to_datetime(resueltos["fecha_creacion"])
            ).dt.total_seconds() / 3600
            resueltos = resueltos.assign(horas=horas)
            resolucion_por_mes = resueltos.groupby("periodo")["horas"].mean().reset_index(name="tiempo_promedio_resolucion_horas")

    satisfaccion = consultas_por_mes.merge(calif_por_mes, on="periodo", how="left")
    satisfaccion = satisfaccion.merge(escalados_por_mes, on="periodo", how="left")
    satisfaccion = satisfaccion.merge(resolucion_por_mes, on="periodo", how="left")
    satisfaccion["categoria"] = "general"
    satisfaccion["calificacion_promedio"] = satisfaccion["calificacion_promedio"].fillna(0).round(2)
    satisfaccion["casos_escalados"] = satisfaccion["casos_escalados"].fillna(0)
    satisfaccion["tasa_escalacion"] = (
        satisfaccion["casos_escalados"] / satisfaccion["total_consultas"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)
    satisfaccion["tiempo_promedio_resolucion_horas"] = satisfaccion["tiempo_promedio_resolucion_horas"].fillna(0).round(2)
    satisfaccion["total_consultas"] = satisfaccion["total_consultas"].astype("uint32")
    satisfaccion = satisfaccion.dropna(subset=["periodo"])
    satisfaccion = satisfaccion[columnas_sat]

    salidas = {"agg_disrupciones_aerolinea_ruta": disrup, "agg_satisfaccion_soporte": satisfaccion}
    for tabla, resultado in salidas.items():
        ch.escribir_parquet(resultado, _nombre_archivo(tabla, marca), config.PARQUET_PROCESANDO)
        print(f"[transformar] {tabla}: {len(resultado)} filas")

    for base in archivos_todos:
        (config.PARQUET_PROCESANDO / _nombre_archivo(base, marca)).unlink(missing_ok=True)

    return {"marca": marca, "filas": {t: len(r) for t, r in salidas.items()}}


def cargar(transformado: dict) -> dict:
    marca = transformado["marca"]
    tablas = ["agg_disrupciones_aerolinea_ruta", "agg_satisfaccion_soporte"]

    resultado: dict[str, int] = {}
    for tabla in tablas:
        nombre = _nombre_archivo(tabla, marca)
        df = pd.read_parquet(config.PARQUET_PROCESANDO / nombre)
        insertadas = ch.insertar_df(f"aerotrack_travel.{tabla}", df)
        ch.mover_parquet(nombre, config.PARQUET_PROCESANDO, config.PARQUET_TERMINADO)
        resultado[tabla] = insertadas
        print(f"[cargar] {tabla}: {insertadas} filas insertadas en ClickHouse")

    return resultado
