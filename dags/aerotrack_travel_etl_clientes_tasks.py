"""
AeroTrack Travel — ETL clientes: MinIO operacional (vía /internal/analitica)
-> ClickHouse
===============================================================================
DAG `aerotrack_travel_etl_clientes`. Alimenta `agg_segmentos_pasajero` y
`agg_alertas_conversion`.

Decisiones de diseño:
- `destino_frecuente` se resuelve por tipo de producto: vuelo (destino del
  vuelo), hotel/auto/actividad (ciudad del catálogo). Crucero queda sin
  resolver — no tiene un único "destino" simple (es un itinerario de
  puertos), y hoy no hay ningún `reserva_item` de tipo crucero para
  validar contra datos reales de todas formas.
- `total_conversiones` de una alerta = reservas del mismo pasajero, en la
  misma ruta (origen+destino), creadas DESPUÉS de que se creó la alerta —
  no hay un campo directo que vincule una alerta con "la" reserva que
  disparó, se infiere por ruta+tiempo.
"""

from __future__ import annotations

import datetime

import clickhouse_client as ch
import config
import pandas as pd
import pocketbase_client
import requests

ARCHIVOS = ["pasajeros", "reservas", "reserva-items", "alertas-precio"]
CATALOGOS = {
    "vuelos_catalogo": ("vuelo_id", "destino_codigo"),
    "hoteles_catalogo": ("hotel_id", "ciudad"),
    "autos_catalogo": ("auto_id", "ciudad_recogida"),
    "actividades_catalogo": ("actividad_id", "ciudad"),
}


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

    for coleccion, (_campo_id, campo_destino) in CATALOGOS.items():
        registros = pocketbase_client.list_all(coleccion)
        # Solo id + los campos que se usan — algunos catálogos (ej. hoteles
        # con `category_scores` vacío) traen columnas con tipos que pyarrow
        # no puede escribir a Parquet, y no hacen falta para este DAG.
        # `vuelos_catalogo` necesita también `origen_codigo` (para el match
        # de ruta de `agg_alertas_conversion`, no solo el destino).
        campos = ["id", campo_destino] if coleccion != "vuelos_catalogo" else ["id", "origen_codigo", campo_destino]
        df = pd.DataFrame([{c: r.get(c) for c in campos} for r in registros])
        ch.escribir_parquet(df, _nombre_archivo(coleccion, marca), config.PARQUET_E)
        conteos[coleccion] = len(df)

    print(f"[extraer] marca={marca} {conteos}")
    return {"marca": marca, "conteos": conteos}


def _mes_a_periodo(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, errors="coerce").dt.to_period("M").dt.to_timestamp().dt.date


def _moda(serie: pd.Series):
    limpio = serie.dropna()
    if limpio.empty:
        return None
    return limpio.mode().iloc[0]


def transformar(extraido: dict) -> dict:
    marca = extraido["marca"]
    archivos_todos = ARCHIVOS + list(CATALOGOS)

    dataframes = {}
    for base in archivos_todos:
        nombre = _nombre_archivo(base, marca)
        dataframes[base] = pd.read_parquet(config.PARQUET_E / nombre)
        ch.mover_parquet(nombre, config.PARQUET_E, config.PARQUET_T)

    pasajeros = dataframes["pasajeros"]
    reservas = dataframes["reservas"]
    items = dataframes["reserva-items"]
    alertas = dataframes["alertas-precio"]

    # ── agg_segmentos_pasajero ───────────────────────────────────────
    columnas_seg = [
        "pasajero_id", "total_reservas", "primera_reserva", "ultima_reserva",
        "destino_frecuente", "tipo_producto_frecuente", "gasto_total", "segmento",
    ]
    if not reservas.empty and not pasajeros.empty:
        # destino por ítem, según su tipo de producto y el catálogo correspondiente
        items = items.copy()
        items["destino"] = None
        for coleccion, (campo_id, campo_destino) in CATALOGOS.items():
            catalogo = dataframes[coleccion]
            if catalogo.empty or campo_id not in items.columns:
                continue
            mapa = catalogo.set_index("id")[campo_destino].to_dict()
            mask = items[campo_id].notna() if campo_id in items.columns else pd.Series(False, index=items.index)
            items.loc[mask, "destino"] = items.loc[mask, campo_id].map(mapa)

        items_r = items.merge(
            reservas[["id", "pasajero_titular_id", "fecha_reserva", "estado", "total_pagar"]]
            .rename(columns={"id": "reserva_id"}),
            on="reserva_id", how="left",
        )

        por_pasajero = reservas.groupby("pasajero_titular_id").agg(
            total_reservas=("id", "size"),
            primera_reserva=("fecha_reserva", "min"),
            ultima_reserva=("fecha_reserva", "max"),
        ).reset_index().rename(columns={"pasajero_titular_id": "pasajero_id"})
        por_pasajero["primera_reserva"] = pd.to_datetime(por_pasajero["primera_reserva"], errors="coerce").dt.date
        por_pasajero["ultima_reserva"] = pd.to_datetime(por_pasajero["ultima_reserva"], errors="coerce").dt.date

        destinos_frecuentes = items_r.groupby("pasajero_titular_id")["destino"].apply(_moda).reset_index(
            name="destino_frecuente"
        ).rename(columns={"pasajero_titular_id": "pasajero_id"})
        tipos_frecuentes = items_r.groupby("pasajero_titular_id")["tipo_producto"].apply(_moda).reset_index(
            name="tipo_producto_frecuente"
        ).rename(columns={"pasajero_titular_id": "pasajero_id"})

        gasto = reservas[reservas["estado"] == "confirmada"].groupby("pasajero_titular_id")["total_pagar"].sum() \
            .reset_index(name="gasto_total").rename(columns={"pasajero_titular_id": "pasajero_id"})

        segmentos = por_pasajero.merge(destinos_frecuentes, on="pasajero_id", how="left")
        segmentos = segmentos.merge(tipos_frecuentes, on="pasajero_id", how="left")
        segmentos = segmentos.merge(gasto, on="pasajero_id", how="left")
        segmentos["gasto_total"] = segmentos["gasto_total"].fillna(0).round(2)
        segmentos["destino_frecuente"] = segmentos["destino_frecuente"].fillna("")
        segmentos["tipo_producto_frecuente"] = segmentos["tipo_producto_frecuente"].fillna("")

        def _segmento(n: int) -> str:
            if n >= 5:
                return "frecuente"
            if n >= 2:
                return "recurrente"
            return "nuevo"

        segmentos["segmento"] = segmentos["total_reservas"].apply(_segmento)
        segmentos["total_reservas"] = segmentos["total_reservas"].astype("uint32")
        segmentos = segmentos[columnas_seg]
    else:
        segmentos = pd.DataFrame(columns=columnas_seg)

    # ── agg_alertas_conversion ────────────────────────────────────────
    columnas_alertas = [
        "periodo", "total_alertas_activas", "total_conversiones",
        "tasa_conversion", "tiempo_promedio_conversion_horas",
    ]
    if not alertas.empty:
        alertas = alertas.copy()
        alertas["periodo"] = _mes_a_periodo(alertas["created"])
        activas_por_mes = alertas[alertas["activa"] == True].groupby("periodo").size().reset_index(name="total_alertas_activas")  # noqa: E712

        conversiones = []
        if not reservas.empty and "vuelo_id" in reservas.columns:
            vuelos = dataframes["vuelos_catalogo"]
            reservas_v = reservas.merge(
                vuelos[["id", "origen_codigo", "destino_codigo"]].rename(columns={"id": "vuelo_id"}),
                on="vuelo_id", how="left",
            )
            for alerta in alertas.itertuples():
                candidatas = reservas_v[
                    (reservas_v["pasajero_titular_id"] == getattr(alerta, "pasajero_id", None))
                    & (reservas_v["origen_codigo"] == getattr(alerta, "origen_codigo", None))
                    & (reservas_v["destino_codigo"] == getattr(alerta, "destino_codigo", None))
                    & (reservas_v["fecha_reserva"] > alerta.created)
                ]
                if not candidatas.empty:
                    primera = pd.to_datetime(candidatas["fecha_reserva"]).min()
                    horas = (primera - pd.to_datetime(alerta.created)).total_seconds() / 3600
                    conversiones.append({"periodo": alerta.periodo, "horas": horas})

        conv_df = pd.DataFrame(conversiones)
        if not conv_df.empty:
            conversiones_por_mes = conv_df.groupby("periodo").agg(
                total_conversiones=("horas", "size"), tiempo_promedio_conversion_horas=("horas", "mean"),
            ).reset_index()
        else:
            conversiones_por_mes = pd.DataFrame(columns=["periodo", "total_conversiones", "tiempo_promedio_conversion_horas"])

        agg_alertas = activas_por_mes.merge(conversiones_por_mes, on="periodo", how="outer")
        agg_alertas["total_alertas_activas"] = agg_alertas["total_alertas_activas"].fillna(0).astype("uint32")
        agg_alertas["total_conversiones"] = agg_alertas["total_conversiones"].fillna(0).astype("uint32")
        agg_alertas["tiempo_promedio_conversion_horas"] = agg_alertas["tiempo_promedio_conversion_horas"].fillna(0).round(2)
        agg_alertas["tasa_conversion"] = (
            agg_alertas["total_conversiones"] / agg_alertas["total_alertas_activas"].replace(0, pd.NA) * 100
        ).fillna(0).round(2)
        agg_alertas = agg_alertas.dropna(subset=["periodo"])
        agg_alertas = agg_alertas[columnas_alertas]
    else:
        agg_alertas = pd.DataFrame(columns=columnas_alertas)

    salidas = {"agg_segmentos_pasajero": segmentos, "agg_alertas_conversion": agg_alertas}
    for tabla, resultado in salidas.items():
        ch.escribir_parquet(resultado, _nombre_archivo(tabla, marca), config.PARQUET_T)
        print(f"[transformar] {tabla}: {len(resultado)} filas")

    for base in archivos_todos:
        (config.PARQUET_T / _nombre_archivo(base, marca)).unlink(missing_ok=True)

    return {"marca": marca, "filas": {t: len(r) for t, r in salidas.items()}}


def cargar(transformado: dict) -> dict:
    marca = transformado["marca"]
    tablas = ["agg_segmentos_pasajero", "agg_alertas_conversion"]

    resultado: dict[str, int] = {}
    for tabla in tablas:
        nombre = _nombre_archivo(tabla, marca)
        df = pd.read_parquet(config.PARQUET_T / nombre)
        insertadas = ch.insertar_df(f"aerotrack_travel.{tabla}", df)
        ch.mover_parquet(nombre, config.PARQUET_T, config.PARQUET_L)
        resultado[tabla] = insertadas
        print(f"[cargar] {tabla}: {insertadas} filas insertadas en ClickHouse")

    return resultado
