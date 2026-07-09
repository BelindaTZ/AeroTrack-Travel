"""
AeroTrack Travel — DAG: Consultar estado real de vuelo (CU-O40)
===================================================================
Qué hace: entre los vuelos_catalogo 'programados' que tienen al menos
una reserva activa (pendiente_pago/confirmada/modificada) y caen dentro
de la ventana de cercanía (configuracion_sistema.api_estado_vuelo.ventana_horas,
48h por defecto — más ajustada que el umbral general de 72h que separa
al simulador estadístico del resto), consulta AviationStack UNA sola vez
por vuelo único (no una vez por reserva) y crea/actualiza disrupciones
si hay cancelación o retraso relevante.

    [probar_conexion] >> [consultar_vuelos_proximos]

Control de cuota (E3, degradación ordenada): cada llamada real pasa por
flight_status_provider.consultar_estado_vuelo(), que verifica el contador
mensual (api_estado_vuelo.llamadas_usadas_mes vs .limite_mensual) ANTES de
llamar a AviationStack. Si ya no hay cupo, degrada al simulador estadístico
en vez de fallar — la fila de disrupciones resultante se atribuye
correctamente a fuente_deteccion='simulador_estadistico' en ese caso, NO
a 'api_real', porque eso es lo que realmente la generó.

Presupuesto de cuota por diseño (no por red de seguridad): plan gratuito
de AviationStack = 100 llamadas/mes, límite operativo configurado en
api_estado_vuelo.limite_mensual = 90 (10 de colchón para pruebas manuales).
Con schedule="@daily", el peor caso por corrida es 1 (probar_conexion) +
MAX_LLAMADAS_POR_CORRIDA (candidatos) llamadas reales. MAX_LLAMADAS_POR_CORRIDA
se fijó en 2 para que ese peor caso (3/día × 30 días = 90) calce exacto
dentro del límite mensual — la cuota no debe agotarse por la aritmética
normal del sistema en un mes típico. El respaldo del simulador estadístico
(E3, ver flight_status_provider.py) sigue existiendo como red de seguridad
genuina para escenarios imprevistos (meses con más candidatos de lo usual,
reintentos, etc.), no como la ruta esperada de funcionamiento.

UI: http://localhost:8081 -> busca "aerotrack_travel_estado_real_vuelo"
"""

from __future__ import annotations

import datetime
from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

import pocketbase_client as pb
from flight_status_provider import consultar_estado_vuelo

MAX_LLAMADAS_POR_CORRIDA = 2
UMBRAL_RETRASO_MIN_RELEVANTE = 15
RESERVAS_ACTIVAS = {"pendiente_pago", "confirmada", "modificada"}


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    print("FALLO EN EL DAG de estado real de vuelo")
    print(f"   Tarea: {ti.task_id if ti else '?'}")
    print(f"   Error: {context.get('exception')}")


@dag(
    dag_id="aerotrack_travel_estado_real_vuelo",
    description="CU-O40: consulta AviationStack (una vez por vuelo único con reserva activa) para vuelos dentro de la ventana de cercanía",
    schedule="@daily",  # activado tras confirmar contador + deduplicación (2026-07-09)
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    dagrun_timeout=timedelta(minutes=10),
    default_args={
        "owner": "aerotrack-travel",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack-travel", "disrupciones", "api-externa", "aviationstack"],
)
def aerotrack_travel_estado_real_vuelo():
    @task(task_id="probar_conexion", execution_timeout=timedelta(seconds=30))
    def probar_conexion() -> dict:
        """Prueba de vida de la integración con un vuelo real conocido.
        Pasa por el mismo gate de cuota que el resto — si la cuota ya
        está agotada, esta prueba también degrada al simulador (correcto:
        no debe consumir cupo "gratis" fuera de la contabilidad)."""
        resultado = consultar_estado_vuelo("AA100")  # American Airlines JFK-LAX, vuelo real diario
        print(f"[ESTADO-REAL] Prueba de conexión -> {resultado}")
        return resultado

    @task(task_id="consultar_vuelos_proximos", execution_timeout=timedelta(minutes=5))
    def consultar_vuelos_proximos(_prueba: dict) -> dict:
        ventana_horas = int(pb.get_config("api_estado_vuelo.ventana_horas", "48"))
        limite = datetime.datetime.utcnow() + datetime.timedelta(hours=ventana_horas)

        # 1) vuelos programados dentro de la ventana de cercanía
        vuelos = pb.list_all("vuelos_catalogo", filter_='estado="programado"')
        vuelos_en_ventana = {}
        for v in vuelos:
            try:
                fecha_salida = datetime.datetime.strptime(v["fecha_salida"][:10], "%Y-%m-%d")
            except (ValueError, KeyError):
                continue
            if fecha_salida <= limite:
                vuelos_en_ventana[v["id"]] = v

        # 2) reservas activas -> qué vuelos tienen al menos un pasajero real
        #    (no tiene sentido gastar cuota en vuelos sin ninguna reserva)
        reservas = pb.list_all("reservas")
        vuelo_ids_con_reserva = {
            r["vuelo_id"] for r in reservas if r.get("estado") in RESERVAS_ACTIVAS
        }

        # 3) intersección = un vuelo único por (numero_vuelo, fecha_salida) ya
        #    que vuelos_catalogo no tiene filas duplicadas por ruta+fecha —
        #    agrupar por reserva colapsa automáticamente aquí, nunca se llama
        #    dos veces por el mismo vuelo aunque tenga varias reservas.
        candidatos = [v for vid, v in vuelos_en_ventana.items() if vid in vuelo_ids_con_reserva]

        consultados = reales = degradados_por_cuota = actualizados = 0
        for v in candidatos[:MAX_LLAMADAS_POR_CORRIDA]:
            resultado = consultar_estado_vuelo(v["numero_vuelo"])
            consultados += 1
            es_degradado = resultado.get("proveedor") == "simulador_fallback"
            if es_degradado:
                degradados_por_cuota += 1
            else:
                reales += 1

            if not resultado.get("encontrado"):
                continue

            fuente = "simulador_estadistico" if es_degradado else "api_real"
            disparar = False
            tipo_cambio = "retraso"
            detalle = ""
            probabilidad = None

            if es_degradado:
                riesgo = resultado.get("probabilidad_riesgo_simulada")
                umbral_riesgo = float(pb.get_config("simulador_disrupciones.umbral_riesgo_pct", "20"))
                if riesgo is not None and riesgo >= umbral_riesgo:
                    disparar = True
                    probabilidad = riesgo
                    detalle = f"Respaldo por cuota agotada de AviationStack: riesgo estimado {riesgo}% (simulador)"
            else:
                retraso = resultado.get("retraso_min") or 0
                if resultado.get("cancelado") or retraso >= UMBRAL_RETRASO_MIN_RELEVANTE:
                    disparar = True
                    tipo_cambio = "cancelacion" if resultado.get("cancelado") else "retraso"
                    detalle = f"AviationStack: estado={resultado.get('estado_raw')}, retraso={retraso} min"

            if disparar:
                existente = pb.get_first("disrupciones", f'vuelo_id="{v["id"]}" && fuente_deteccion="{fuente}"')
                payload = {
                    "probabilidad": probabilidad,
                    "detalle": detalle,
                    "estado": "activa",
                    "fecha_deteccion": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z"),
                }
                if existente:
                    pb.update("disrupciones", existente["id"], payload)
                else:
                    pb.create("disrupciones", {
                        "vuelo_id": v["id"], "fuente_deteccion": fuente,
                        "tipo_cambio": tipo_cambio, **payload,
                    })
                actualizados += 1

        resumen = {
            "vuelos_en_ventana": len(vuelos_en_ventana),
            "reservas_activas_evaluadas": len(reservas),
            "vuelos_unicos_con_reserva_en_ventana": len(candidatos),
            "consultados": consultados,
            "llamadas_reales": reales,
            "degradados_por_cuota": degradados_por_cuota,
            "disrupciones_detectadas": actualizados,
        }
        print(f"[ESTADO-REAL] {resumen}")
        return resumen

    prueba = probar_conexion()
    consultar_vuelos_proximos(prueba)


dag_instance = aerotrack_travel_estado_real_vuelo()
