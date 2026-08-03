"""
AeroTrack Travel — Tareas del módulo Vuelos (catálogo)
=========================================================
Implementa las dos automatizaciones que el catálogo de casos de uso
operativos asigna explícitamente a "Sistema (automático)":

  - CU-O30: Generar catálogo de vuelos programables (marcado como
    "Sistema (automático, Airflow)" en el catálogo de CU).
  - CU-O31: Actualizar estado de un vuelo (versión de esta entrega:
    transición programado -> completado por horario vencido; la
    consulta a una API de estado real en tiempo real es CU-O40 y
    depende de credenciales que todavía no se configuran, CU-O17).

Fuente de datos: dim_ruta (rutas reales) leído en modo solo lectura
desde aerotrack-travel-dims (principio A2 de la constitución). Las
aerolíneas y niveles de tarifa se leen del catálogo operativo nuevo
en pocketbase-travel (aerolineas, niveles_tarifa) — nunca del modelo
dimensional directamente, para no mezclar dominios (A1).
"""

from __future__ import annotations

import datetime

import pocketbase_client as pb
from minio_dims_reader import read_parquet

# Aeropuertos hub sobre los que se arma el catálogo (alcance doméstico EE.UU.,
# consistente con el dataset BTS/FAA). Acotar a hubs mantiene el catálogo en
# un tamaño manejable en vez de generar miles de rutas irrelevantes.
HUBS = [
    "ATL", "ORD", "DFW", "DEN", "LAX", "JFK", "SFO", "LAS",
    "MCO", "PHX", "MIA", "SEA", "EWR", "CLT", "IAH",
]
MAX_RUTAS = 20
HORIZONTE_DIAS = 7


def _rutas_curadas() -> list[dict]:
    """Rutas reales entre hubs, leídas de dim_ruta (solo lectura). Selección
    round-robin por aeropuerto de origen — con orden alfabético + head(N)
    (versión anterior), ATL y CLT agotaban todo el cupo de MAX_RUTAS antes
    de que cualquier otro de los 15 hubs llegara a aparecer como origen
    (bug confirmado, ver docs/aerotrack-travel-propuesta-tablas-v3.dbml:
    147-156). El round-robin garantiza que todo hub con al menos una ruta
    real hacia otro hub del catálogo aparezca como origen."""
    df = read_parquet("dim_ruta", ["OriginCode", "DestCode", "Distance", "OriginCityName", "DestCityName"])
    df = df[df["OriginCode"].isin(HUBS) & df["DestCode"].isin(HUBS)]
    df = df.sort_values(["OriginCode", "DestCode"]).drop_duplicates(subset=["OriginCode", "DestCode"])

    por_origen: dict[str, list[dict]] = {}
    for registro in df.to_dict("records"):
        por_origen.setdefault(registro["OriginCode"], []).append(registro)

    rutas: list[dict] = []
    while len(rutas) < MAX_RUTAS and any(por_origen.values()):
        for origen in HUBS:
            candidatas = por_origen.get(origen)
            if not candidatas:
                continue
            rutas.append(candidatas.pop(0))
            if len(rutas) >= MAX_RUTAS:
                break
    return rutas


def generar_vuelos_programables() -> int:
    """CU-O30. Idempotente: asegura que exista un vuelo por ruta curada
    para cada uno de los próximos HORIZONTE_DIAS días. Cada corrida diaria
    extiende el horizonte de reserva un día más (rolling window)."""
    rutas = _rutas_curadas()
    aerolineas = pb.list_all("aerolineas", filter_="activa=true")
    niveles = pb.list_all("niveles_tarifa")
    if not aerolineas:
        raise RuntimeError("No hay aerolíneas activas en pocketbase-travel. Ejecuta el seed inicial primero.")
    if len(niveles) != 3:
        print(f"[CATALOGO] ⚠ se esperaban 3 niveles_tarifa, hay {len(niveles)}")

    hoy = datetime.date.today()
    creados = 0

    for idx, ruta in enumerate(rutas):
        aerolinea = aerolineas[idx % len(aerolineas)]
        numero_vuelo = f"{aerolinea['codigo_iata']}{1000 + idx * 37}"
        distancia = float(ruta.get("Distance") or 0)
        duracion_min = round(distancia / 450 * 60) + 25
        hora_salida_h = 6 + (idx % 10)
        precio_base = round(79 + distancia * 0.115, 2)

        for dia_offset in range(1, HORIZONTE_DIAS + 1):
            fecha_salida = hoy + datetime.timedelta(days=dia_offset)
            fecha_salida_iso = fecha_salida.strftime("%Y-%m-%d 00:00:00.000Z")

            ya_existe = pb.get_first(
                "vuelos_catalogo",
                f'numero_vuelo="{numero_vuelo}" && fecha_salida="{fecha_salida_iso}"',
            )
            if ya_existe:
                continue

            hora_llegada_dt = (
                datetime.datetime.combine(fecha_salida, datetime.time(hora_salida_h, 0))
                + datetime.timedelta(minutes=duracion_min)
            )
            vuelo = pb.create("vuelos_catalogo", {
                "numero_vuelo": numero_vuelo,
                "aerolinea_id": aerolinea["id"],
                "origen_codigo": ruta["OriginCode"],
                "destino_codigo": ruta["DestCode"],
                "fecha_salida": fecha_salida_iso,
                "hora_salida_programada": f"{hora_salida_h:02d}:00",
                "hora_llegada_programada": hora_llegada_dt.strftime("%H:%M"),
                "duracion_min": duracion_min,
                "precio_base": precio_base,
                "estado": "programado",
                "generado_por": "sistema",
                "fecha_actualizacion_estado": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z"),
            })
            creados += 1

            deltas = {"Light": 0.0, "Standard": 60.0, "Flex": 140.0}
            cupos = {"Light": 120, "Standard": 80, "Flex": 30}
            for nivel in niveles:
                nombre = nivel["nombre"]
                pb.create("tarifas_vuelo", {
                    "vuelo_id": vuelo["id"],
                    "nivel_tarifa_id": nivel["id"],
                    "precio_final": round(precio_base + deltas.get(nombre, 0.0), 2),
                    "cupos_disponibles": cupos.get(nombre, 50),
                })

    print(f"[CATALOGO] {creados} vuelos_catalogo nuevos (+{creados * 3} tarifas_vuelo) sobre {len(rutas)} rutas curadas")
    return creados


def actualizar_estados_vuelos() -> int:
    """CU-O31 (versión sin API externa): cualquier vuelo 'programado' cuya
    hora de llegada programada ya pasó se marca 'completado'. La detección
    de retrasos/cancelaciones reales es responsabilidad de CU-O39/40/41,
    no de esta tarea."""
    ahora = datetime.datetime.utcnow()
    vuelos = pb.list_all("vuelos_catalogo", filter_='estado="programado"')
    actualizados = 0

    for v in vuelos:
        try:
            fecha_salida = datetime.datetime.strptime(v["fecha_salida"][:10], "%Y-%m-%d").date()
            hora_h, hora_m = (int(x) for x in v["hora_llegada_programada"].split(":"))
        except (ValueError, KeyError):
            continue

        llegada_dt = datetime.datetime.combine(fecha_salida, datetime.time(hora_h, hora_m))
        if v.get("duracion_min") and hora_h < 6:  # cruce de medianoche simplificado
            llegada_dt += datetime.timedelta(days=1)

        if llegada_dt < ahora:
            pb.update("vuelos_catalogo", v["id"], {
                "estado": "completado",
                "fecha_actualizacion_estado": ahora.strftime("%Y-%m-%d %H:%M:%S.000Z"),
            })
            actualizados += 1

    print(f"[CATALOGO] {actualizados} vuelos marcados 'completado'")
    return actualizados
