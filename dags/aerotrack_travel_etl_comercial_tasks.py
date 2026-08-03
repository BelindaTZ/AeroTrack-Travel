"""
AeroTrack Travel — ETL comercial: MinIO operacional (vía /internal/analitica)
-> ClickHouse
================================================================================
DAG `aerotrack_travel_etl_comercial`. Alimenta `agg_ingresos_por_producto_mes`
y `agg_conversion_busqueda_reserva`.

Ningún DAG lee MinIO operacional directo (ver
`dag_estimar_riesgo_disrupcion.py` y `app/shared/router_interno_analitica.py`)
— "extraer" llama a los endpoints internos de la app, que sí tienen acceso
vía sus repositorios.

Decisiones de diseño documentadas acá porque el pedido original dejaba
ambigüedades reales (no hay ningún error de código detrás, son casos que
no tienen una única respuesta correcta):

- `total_reservas`/`ingresos_brutos` cuentan TODOS los `reserva_items` sin
  filtrar por estado de la reserva — un vistazo de demanda/ingreso bruto,
  no de ingreso ya cobrado. `comisiones`/`reembolsos` sí reflejan solo
  movimientos reales (esas colecciones solo tienen filas para eventos que
  de verdad ocurrieron).
- Las comisiones son 100% de vuelos (`comision_service.py` nunca genera
  una comisión para otro tipo de producto) — se atribuyen enteras al
  `tipo_producto='vuelo'` de la reserva.
- Los reembolsos son por RESERVA completa, no por ítem — en una reserva
  con un solo tipo de producto no hay ambigüedad; en un paquete (>1 tipo)
  se reparte proporcional al peso de cada ítem (`precio_final*cantidad`)
  dentro de esa reserva.
- El funnel (`total_busquedas/carritos/checkouts/confirmadas`) cuenta
  ENTIDADES DISTINTAS por etapa (carritos distintos, reservas distintas
  vía pago, reservas distintas confirmadas) — no filas crudas — para que
  las 4 etapas sean comparables entre sí.
- `total_checkouts` = pagos creados (momento del PaymentIntent, confirmado
  con el usuario) — un pago de una reserva con >1 tipo de producto
  (paquete) cuenta en el checkout de cada tipo de producto presente.
"""

from __future__ import annotations

import datetime

import clickhouse_client as ch
import config
import pandas as pd
import requests

ARCHIVOS = [
    "reservas", "reserva-items", "carrito-items", "busquedas-recientes",
    "pagos", "facturas", "comisiones", "reembolsos",
]


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
    carrito_items = dataframes["carrito-items"]
    busquedas = dataframes["busquedas-recientes"]
    pagos = dataframes["pagos"]
    comisiones = dataframes["comisiones"]
    reembolsos = dataframes["reembolsos"]

    # Outlier de precio en el catálogo real de cruceros (Cruise Pricing API,
    # `cruceros_camarotes_tarifa.precio_por_persona` hasta $250,703 en algunos
    # camarotes — casi seguro un bug de moneda/unidades en esa integración,
    # fuera de alcance acá) — se descarta antes de agregar ingresos para que
    # no distorsione agg_ingresos_por_producto_mes. El campo real en
    # `reserva_items` es `precio_final`, no `precio_por_persona` (ese nombre
    # es del catálogo crudo).
    if not items.empty:
        antes = len(items)
        items = items[~((items["tipo_producto"] == "crucero") & (items["precio_final"] > 50000))]
        descartados = antes - len(items)
        if descartados:
            print(f"[transformar] descartados {descartados} reserva_items de crucero con precio_final > 50000 (outlier)")

    # ── agg_ingresos_por_producto_mes ────────────────────────────────
    if not items.empty and not reservas.empty:
        items_r = items.merge(
            reservas[["id", "fecha_reserva", "estado"]].rename(columns={"id": "reserva_id"}),
            on="reserva_id", how="left",
        )
        items_r["periodo"] = _mes_a_periodo(items_r["fecha_reserva"])
        items_r["monto_item"] = items_r["precio_final"].fillna(0) * items_r["cantidad"].fillna(1)

        ingresos = items_r.groupby(["periodo", "tipo_producto"]).agg(
            total_reservas=("id", "size"),
            ingresos_brutos=("monto_item", "sum"),
        ).reset_index()

        # comisiones -> 100% al tipo_producto "vuelo" de la reserva que las generó
        if not comisiones.empty:
            com = comisiones[comisiones["reserva_id"].fillna("") != ""].merge(
                reservas[["id", "fecha_reserva"]].rename(columns={"id": "reserva_id"}), on="reserva_id", how="left"
            )
            com["periodo"] = _mes_a_periodo(com["fecha_reserva"])
            com_mes = com.groupby("periodo")["monto"].sum().reset_index(name="comisiones")
            com_mes["tipo_producto"] = "vuelo"
        else:
            com_mes = pd.DataFrame(columns=["periodo", "comisiones", "tipo_producto"])

        # reembolsos -> repartidos proporcional al peso de cada item en su reserva
        if not reembolsos.empty and not items_r.empty:
            peso_reserva = items_r.groupby("reserva_id")["monto_item"].transform("sum")
            items_r["peso"] = (items_r["monto_item"] / peso_reserva.replace(0, pd.NA)).fillna(1.0)
            reemb = reembolsos.merge(
                items_r[["reserva_id", "tipo_producto", "periodo", "peso"]], on="reserva_id", how="inner"
            )
            reemb["monto_atribuido"] = reemb["monto"] * reemb["peso"]
            reemb_mes = reemb.groupby(["periodo", "tipo_producto"])["monto_atribuido"].sum().reset_index(name="reembolsos")
        else:
            reemb_mes = pd.DataFrame(columns=["periodo", "tipo_producto", "reembolsos"])

        ingresos = ingresos.merge(com_mes, on=["periodo", "tipo_producto"], how="left")
        ingresos = ingresos.merge(reemb_mes, on=["periodo", "tipo_producto"], how="left")
        ingresos["comisiones"] = ingresos["comisiones"].fillna(0).round(2)
        ingresos["reembolsos"] = ingresos["reembolsos"].fillna(0).round(2)
        ingresos["ingresos_brutos"] = ingresos["ingresos_brutos"].round(2)
        ingresos["ingresos_netos"] = (ingresos["ingresos_brutos"] - ingresos["reembolsos"]).round(2)
        ingresos["total_reservas"] = ingresos["total_reservas"].astype("uint32")
        ingresos = ingresos[["periodo", "tipo_producto", "total_reservas", "ingresos_brutos", "comisiones", "reembolsos", "ingresos_netos"]]
        ingresos = ingresos.dropna(subset=["periodo"])
    else:
        ingresos = pd.DataFrame(columns=["periodo", "tipo_producto", "total_reservas", "ingresos_brutos", "comisiones", "reembolsos", "ingresos_netos"])

    # ── agg_conversion_busqueda_reserva ──────────────────────────────
    partes_busquedas = pd.DataFrame(columns=["periodo", "tipo_producto", "total_busquedas"])
    if not busquedas.empty:
        busquedas["periodo"] = _mes_a_periodo(busquedas["fecha"])
        partes_busquedas = busquedas.groupby(["periodo", "tipo_producto"]).size().reset_index(name="total_busquedas")

    partes_carritos = pd.DataFrame(columns=["periodo", "tipo_producto", "total_carritos"])
    if not carrito_items.empty:
        carrito_items["periodo"] = _mes_a_periodo(carrito_items["fecha_agregado"])
        partes_carritos = carrito_items.groupby(["periodo", "tipo_producto"])["carrito_id"].nunique().reset_index(name="total_carritos")

    partes_checkouts = pd.DataFrame(columns=["periodo", "tipo_producto", "total_checkouts"])
    if not pagos.empty and not items.empty and not reservas.empty:
        pagos_r = pagos.merge(
            reservas[["id", "fecha_reserva"]].rename(columns={"id": "reserva_id"}), on="reserva_id", how="left"
        )
        pagos_tipo = pagos_r.merge(items[["reserva_id", "tipo_producto"]].drop_duplicates(), on="reserva_id", how="inner")
        pagos_tipo["periodo"] = _mes_a_periodo(pagos_tipo["fecha_reserva"])
        partes_checkouts = pagos_tipo.groupby(["periodo", "tipo_producto"])["reserva_id"].nunique().reset_index(name="total_checkouts")

    partes_confirmadas = pd.DataFrame(columns=["periodo", "tipo_producto", "total_confirmadas"])
    if not items.empty and not reservas.empty:
        confirmadas = reservas[reservas["estado"] == "confirmada"][["id", "fecha_reserva"]].rename(columns={"id": "reserva_id"})
        conf_items = confirmadas.merge(items[["reserva_id", "tipo_producto"]].drop_duplicates(), on="reserva_id", how="inner")
        conf_items["periodo"] = _mes_a_periodo(conf_items["fecha_reserva"])
        partes_confirmadas = conf_items.groupby(["periodo", "tipo_producto"])["reserva_id"].nunique().reset_index(name="total_confirmadas")

    conversion = partes_busquedas.merge(partes_carritos, on=["periodo", "tipo_producto"], how="outer")
    conversion = conversion.merge(partes_checkouts, on=["periodo", "tipo_producto"], how="outer")
    conversion = conversion.merge(partes_confirmadas, on=["periodo", "tipo_producto"], how="outer")
    conversion = conversion.dropna(subset=["periodo"])
    for col in ["total_busquedas", "total_carritos", "total_checkouts", "total_confirmadas"]:
        conversion[col] = conversion[col].fillna(0).astype("uint32")

    conversion["tasa_conversion_busqueda_reserva"] = (
        conversion["total_confirmadas"] / conversion["total_busquedas"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)
    conversion["tasa_abandono_carrito"] = (
        (conversion["total_carritos"] - conversion["total_confirmadas"]) / conversion["total_carritos"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)
    conversion = conversion[[
        "periodo", "tipo_producto", "total_busquedas", "total_carritos", "total_checkouts",
        "total_confirmadas", "tasa_conversion_busqueda_reserva", "tasa_abandono_carrito",
    ]]

    salidas = {"agg_ingresos_por_producto_mes": ingresos, "agg_conversion_busqueda_reserva": conversion}
    for tabla, resultado in salidas.items():
        ch.escribir_parquet(resultado, _nombre_archivo(tabla, marca), config.PARQUET_PROCESANDO)
        print(f"[transformar] {tabla}: {len(resultado)} filas")

    for base in ARCHIVOS:
        (config.PARQUET_PROCESANDO / _nombre_archivo(base, marca)).unlink(missing_ok=True)

    return {"marca": marca, "filas": {t: len(r) for t, r in salidas.items()}}


def cargar(transformado: dict) -> dict:
    marca = transformado["marca"]
    tablas = ["agg_ingresos_por_producto_mes", "agg_conversion_busqueda_reserva"]

    resultado: dict[str, int] = {}
    for tabla in tablas:
        nombre = _nombre_archivo(tabla, marca)
        df = pd.read_parquet(config.PARQUET_PROCESANDO / nombre)
        insertadas = ch.insertar_df(f"aerotrack_travel.{tabla}", df)
        ch.mover_parquet(nombre, config.PARQUET_PROCESANDO, config.PARQUET_TERMINADO)
        resultado[tabla] = insertadas
        print(f"[cargar] {tabla}: {insertadas} filas insertadas en ClickHouse")

    return resultado
