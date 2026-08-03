"""
Limpia las tablas ClickHouse `agg_ingresos_por_producto_mes` y
`agg_paquetes_margen_mes` (100% derivadas del ETL) y las regenera desde
cero, para eliminar filas huérfanas dejadas por el outlier de precios de
crucero (ver docs/etl-clickhouse-auditoria.md / fix del 2026-08-02).

Por qué hace falta un TRUNCATE y no alcanza con OPTIMIZE ... FINAL:
ReplacingMergeTree solo reemplaza una fila vieja cuando llega una fila
NUEVA con la misma clave de orden. Al filtrar el ítem outlier de crucero
(precio_final > 50000), algunas combinaciones cambiaron de clave (ej.
"auto+crucero" -> "auto" al desaparecer el ítem de crucero), así que la
fila vieja inflada queda huérfana — nada la reemplaza — y sobrevive a
cualquier OPTIMIZE FINAL. Como son tablas derivadas (no fuente de verdad),
truncar y re-correr el DAG es seguro y más simple que borrar filas
puntuales.

Uso:
    python scripts/limpiar_outliers_crucero.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "dags"))

import clickhouse_client as ch  # noqa: E402

TABLAS = ["agg_ingresos_por_producto_mes", "agg_paquetes_margen_mes"]
CONTENEDOR_AIRFLOW = "airflow-scheduler-travel"
DAGS = ["aerotrack_travel_etl_comercial", "aerotrack_travel_etl_finanzas"]


def truncar():
    print("== Truncando tablas ==")
    for tabla in TABLAS:
        ch.ejecutar_query(f"TRUNCATE TABLE aerotrack_travel.{tabla}")
        print(f"  {tabla}: truncada")


def disparar_dags():
    print("== Re-disparando DAGs ==")
    for dag in DAGS:
        subprocess.run(
            ["docker", "exec", CONTENEDOR_AIRFLOW, "airflow", "dags", "trigger", dag],
            check=True,
        )
        print(f"  {dag}: disparado")


def esperar_y_mostrar_estado(segundos: int = 30):
    print(f"== Esperando {segundos}s a que terminen ==")
    time.sleep(segundos)
    for dag in DAGS:
        print(f"-- {dag} --")
        subprocess.run(
            ["docker", "exec", CONTENEDOR_AIRFLOW, "airflow", "dags", "list-runs",
             "-d", dag, "--state", "running,queued,success,failed"],
            check=False,
        )


def verificar():
    print("== Verificación final ==")
    for tabla in TABLAS:
        ch.ejecutar_query(f"OPTIMIZE TABLE aerotrack_travel.{tabla} FINAL")

    print("-- max ingresos_brutos por tipo_producto --")
    for fila in ch.ejecutar_query(
        "SELECT tipo_producto, max(ingresos_brutos) FROM aerotrack_travel.agg_ingresos_por_producto_mes "
        "GROUP BY tipo_producto ORDER BY 2 DESC"
    ):
        print(f"  {fila}")

    print("-- max ingresos_brutos en paquetes --")
    print(f"  {ch.ejecutar_query('SELECT max(ingresos_brutos) FROM aerotrack_travel.agg_paquetes_margen_mes')}")

    print("-- filas totales --")
    for tabla in TABLAS:
        total = ch.ejecutar_query(f"SELECT count() FROM aerotrack_travel.{tabla}")
        print(f"  {tabla}: {total}")


if __name__ == "__main__":
    truncar()
    disparar_dags()
    esperar_y_mostrar_estado()
    verificar()
    print("\nSi alguna corrida seguía en 'running' arriba, corré de nuevo solo verificar()"
          " esperando un poco más antes de confiar en estos números.")
