"""
AeroTrack Travel — ETL finanzas: MinIO operacional (vía /internal/analitica)
-> ClickHouse
===============================================================================
DAG `aerotrack_travel_etl_finanzas`. Alimenta `agg_paquetes_margen_mes`
(único DAG que usa `reservas`/`reserva_items`/`facturas`/`comisiones`/
`remesas` con foco en paquetes — el resto de esas colecciones ya las
consume `aerotrack_travel_etl_comercial` para ingresos generales).

Gap real de datos, no de código: no existe NINGÚN campo de costo de
componente en todo el proyecto (ni en `reserva_items`, ni en los 5
catálogos de producto) — `costo_componentes` no tiene ninguna fuente real
para calcularse. Se deja en 0 (así que `margen_bruto == ingresos_brutos` y
`margen_porcentaje == 100`, ambos sin significado real hoy) — no es una
aproximación razonable como las de los otros DAGs, es directamente un dato
que no existe en el esquema. Si hace falta un margen real para Fase C, hay
que decidir de dónde sale el costo (¿% fijo asumido? ¿campo nuevo en cada
catálogo de producto?) antes de que este número signifique algo.

En la práctica esto no bloquea nada hoy: 0 reservas tienen `es_paquete=True`
en la base actual, así que la tabla sale vacía de cualquier forma — el
gap importa recién cuando B.6 siembre paquetes de verdad.
"""

from __future__ import annotations

import datetime

import clickhouse_client as ch
import config
import pandas as pd
import requests

ARCHIVOS = ["reservas", "reserva-items"]


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
    print(f"[extraer] marca={marca} {conteos}")
    return {"marca": marca, "conteos": conteos}


def _mes_a_periodo(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, errors="coerce").dt.to_period("M").dt.to_timestamp().dt.date


def transformar(extraido: dict) -> dict:
    marca = extraido["marca"]

    dataframes = {}
    for base in ARCHIVOS:
        nombre = _nombre_archivo(base, marca)
        dataframes[base] = pd.read_parquet(config.PARQUET_CRUDO / nombre)
        ch.mover_parquet(nombre, config.PARQUET_CRUDO, config.PARQUET_PROCESANDO)

    reservas = dataframes["reservas"]
    items = dataframes["reserva-items"]

    # Outlier de precio en el catálogo real de cruceros (Cruise Pricing API)
    # — ver misma nota en aerotrack_travel_etl_comercial_tasks.py. Se
    # descarta antes de calcular márgenes de paquete.
    if not items.empty:
        antes = len(items)
        items = items[~((items["tipo_producto"] == "crucero") & (items["precio_final"] > 50000))]
        descartados = antes - len(items)
        if descartados:
            print(f"[transformar] descartados {descartados} reserva_items de crucero con precio_final > 50000 (outlier)")

    columnas = [
        "periodo", "tipo_combinacion", "total_vendidos", "ingresos_brutos",
        "costo_componentes", "margen_bruto", "margen_porcentaje",
    ]
    paquetes = reservas[reservas.get("es_paquete", pd.Series(dtype=bool)) == True] if "es_paquete" in reservas.columns else reservas.iloc[0:0]  # noqa: E712

    if not paquetes.empty and not items.empty:
        items_p = items.merge(
            paquetes[["id", "fecha_reserva"]].rename(columns={"id": "reserva_id"}), on="reserva_id", how="inner"
        )
        items_p["monto_item"] = items_p["precio_final"].fillna(0) * items_p["cantidad"].fillna(1)
        items_p["periodo"] = _mes_a_periodo(items_p["fecha_reserva"])

        combinacion_por_reserva = items_p.groupby("reserva_id")["tipo_producto"].apply(
            lambda s: "+".join(sorted(s.dropna().unique()))
        ).reset_index(name="tipo_combinacion")
        ingresos_por_reserva = items_p.groupby("reserva_id").agg(
            ingresos_brutos=("monto_item", "sum"), periodo=("periodo", "first"),
        ).reset_index()

        por_reserva = ingresos_por_reserva.merge(combinacion_por_reserva, on="reserva_id")
        margen = por_reserva.groupby(["periodo", "tipo_combinacion"]).agg(
            total_vendidos=("reserva_id", "nunique"),
            ingresos_brutos=("ingresos_brutos", "sum"),
        ).reset_index()
        margen["costo_componentes"] = 0.0  # sin fuente real — ver docstring
        margen["margen_bruto"] = (margen["ingresos_brutos"] - margen["costo_componentes"]).round(2)
        margen["margen_porcentaje"] = (
            margen["margen_bruto"] / margen["ingresos_brutos"].replace(0, pd.NA) * 100
        ).fillna(0).round(2)
        margen["ingresos_brutos"] = margen["ingresos_brutos"].round(2)
        margen["total_vendidos"] = margen["total_vendidos"].astype("uint32")
        margen = margen.dropna(subset=["periodo"])
        margen = margen[columnas]
    else:
        margen = pd.DataFrame(columns=columnas)

    ch.escribir_parquet(margen, _nombre_archivo("agg_paquetes_margen_mes", marca), config.PARQUET_PROCESANDO)
    print(f"[transformar] agg_paquetes_margen_mes: {len(margen)} filas")

    for base in ARCHIVOS:
        (config.PARQUET_PROCESANDO / _nombre_archivo(base, marca)).unlink(missing_ok=True)

    return {"marca": marca, "filas": {"agg_paquetes_margen_mes": len(margen)}}


def cargar(transformado: dict) -> dict:
    marca = transformado["marca"]
    nombre = _nombre_archivo("agg_paquetes_margen_mes", marca)
    df = pd.read_parquet(config.PARQUET_PROCESANDO / nombre)
    insertadas = ch.insertar_df("aerotrack_travel.agg_paquetes_margen_mes", df)
    ch.mover_parquet(nombre, config.PARQUET_PROCESANDO, config.PARQUET_TERMINADO)
    print(f"[cargar] agg_paquetes_margen_mes: {insertadas} filas insertadas en ClickHouse")
    return {"agg_paquetes_margen_mes": insertadas}
