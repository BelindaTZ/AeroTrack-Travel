"""RF-VUE-??? — enriquecimiento REAL del catálogo de vuelos (AeroDataBox +
Google Flights/SerpApi), documentado desde el 17 de julio en
`docs/fuentes-datos-por-tabla.md` pero nunca conectado hasta ahora.

Principio rector: `catalogo_vuelos_tasks.generar_vuelos_programables()`
(sintético, por fórmula) sigue siendo la base — garantiza que exista un
vuelo por ruta curada para los próximos 7 días (CU-O30), y ese invariante
NUNCA depende de que estas dos funciones tengan cupo real. Cuando sí hay
cupo, reemplazan valores sintéticos por reales en los mismos registros
(`generado_por` pasa a `sistema_api_real`) — nunca crean rutas nuevas
fuera de las 20 ya curadas, nunca dejan una ruta sin vuelo.

Cada función solo enriquece la fecha de HOY por ruta/hub — el resto de la
ventana de 7 días se pone al día naturalmente a medida que la ventana
rueda y "hoy" pasa por cada fecha (mismo criterio de simplicidad que ya
usa la rotación de ciudades en Hoteles/Actividades/Autos).
"""

import datetime

from app.shared.cuota_service import hay_cupo
from app.shared.rotacion_ciudades import rebanada_rotativa
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.aerodatabox_client import AeroDataBoxClient
from app.vuelos.services.google_flights_client import GoogleFlightsClient

HUBS_DEFAULT = [
    "ATL", "ORD", "DFW", "DEN", "LAX", "JFK", "SFO", "LAS",
    "MCO", "PHX", "MIA", "SEA", "EWR", "CLT", "IAH",
]
HUBS_POR_CORRIDA_DEFAULT = 3
# RF-VUE-010 (CU-O114): desde que se agregó clase de cabina, cada ruta hace
# hasta 3 llamadas (economy/business/first) en vez de 1 — bajado de 3 a 2
# rutas/día para no pasarse del presupuesto de 250/mes (2×3×30 ≈ 180/mes,
# con margen; a 3 rutas/día serían ~270/mes, por encima del techo).
RUTAS_POR_CORRIDA_DEFAULT = 2
CLASES_CABINA = ("economy", "business", "first")
# RF-VUE-T06 (CU-T41) — qué clases participan de la rotación diaria; un
# Administrador puede apagar business/first temporalmente (p. ej. para
# estirar la cuota mensual) sin tocar código. Economy no se ofrece como
# apagable en la UI (es la base de precio_base/predicciones), pero el
# parseo no lo fuerza — respeta lo que el admin haya guardado.
CLASES_ACTIVAS_DEFAULT = CLASES_CABINA
# RN confirmada: Business/First siempre se venden en condiciones Flex (RF-VUE-010)
# — evita crear 3 niveles × 2 clases premium = 6 tarifas nuevas por vuelo cuando
# Google Flights solo da un precio por clase, no por nivel de tarifa.
NIVEL_PREMIUM_NOMBRE = "Flex"
CUPOS_PREMIUM_DEFAULT = {"business": 16, "first": 8}

_NIVEL_A_TENDENCIA = {"low": "bajando", "typical": "estable", "high": "subiendo"}


def _ahora_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z")


async def enriquecer_con_aerodatabox(
    client: AeroDataBoxClient, hoy: datetime.date | None = None, hubs: list[str] | None = None
) -> dict:
    repo = VuelosRepository()
    hoy = hoy or datetime.date.today()

    valor = await repo.config("vuelos.aerodatabox_hubs")
    universo = [h.strip() for h in valor.split(",")] if valor else HUBS_DEFAULT
    if hubs is None:
        valor_corrida = await repo.config("vuelos.aerodatabox_hubs_por_corrida")
        hubs_por_corrida = int(valor_corrida) if valor_corrida else HUBS_POR_CORRIDA_DEFAULT
        hubs = rebanada_rotativa(universo, hubs_por_corrida, hoy)

    fuente = await repo.fuente_por_nombre("AeroDataBox")
    fecha_inicio = _ahora_iso()
    procesados = actualizados = 0
    error_detalle = None
    motivo_parcial = None

    try:
        for hub in hubs:
            if fuente and not await hay_cupo(
                fuente["id"], fuente.get("cuota_mensual_estimada"), getattr(client, "llamadas_realizadas", 0)
            ):
                motivo_parcial = "cuota_mensual_agotada"
                break

            salidas: list[dict] = []
            for bloque in (0, 12):
                desde = datetime.datetime.combine(hoy, datetime.time(bloque, 0))
                hasta = desde + datetime.timedelta(hours=11, minutes=59)
                salidas.extend(
                    await client.salidas(hub, desde.strftime("%Y-%m-%dT%H:%M"), hasta.strftime("%Y-%m-%dT%H:%M"))
                )
            # Las dos ventanas de 12h no deberían solaparse en la vida real,
            # pero deduplicar por número de vuelo es barato y evita procesar
            # el mismo vuelo dos veces si algún día el límite de ventana
            # cambia o un vuelo cae justo en el borde.
            salidas = list({s["numero_vuelo"]: s for s in salidas}.values())

            for salida in salidas:
                procesados += 1
                if salida["destino_codigo"] not in universo:
                    continue  # fuera del universo curado, no interesa

                # RN: reemplaza el vuelo sintético de esa ruta+fecha si ya
                # existe uno programado — nunca crea rutas nuevas.
                candidatos = await repo.buscar(hub, salida["destino_codigo"], hoy.isoformat())
                if not candidatos:
                    continue
                vuelo = candidatos[0]

                cambios = {"generado_por": "sistema_api_real"}
                if salida["avion_modelo"]:
                    cambios["avion_modelo"] = salida["avion_modelo"]
                if salida["hora_salida_local"]:
                    cambios["hora_salida_programada"] = salida["hora_salida_local"]
                if salida["numero_vuelo"]:
                    cambios["numero_vuelo"] = salida["numero_vuelo"]

                await repo.actualizar_vuelo(vuelo["id"], cambios)
                actualizados += 1

        estado = "exitoso" if actualizados > 0 else "parcial"
    except Exception as exc:  # noqa: BLE001 — se registra en la bitácora, no se oculta
        estado = "fallido"
        error_detalle = str(exc)

    if fuente:
        await repo.crear_log_sincronizacion(
            {
                "fuente_id": fuente["id"],
                "tipo_producto": "vuelo",
                "fecha_inicio": fecha_inicio,
                "fecha_fin": _ahora_iso(),
                "estado": estado,
                "registros_procesados": procesados,
                "registros_nuevos": 0,
                "registros_actualizados": actualizados,
                "unidades_cuota_consumidas": getattr(client, "llamadas_realizadas", 0),
                "error_detalle": error_detalle,
            }
        )

    resumen = {"hubs": hubs, "procesados": procesados, "actualizados": actualizados, "estado": estado}
    if motivo_parcial:
        resumen["motivo_parcial"] = motivo_parcial
    if error_detalle:
        resumen["error_detalle"] = error_detalle
    print(f"[VUELOS-AERODATABOX] {resumen}")
    return resumen


async def _clases_activas(repo: VuelosRepository) -> tuple[str, ...]:
    valor = await repo.config("vuelos.google_flights_clases_activas")
    if not valor:
        return CLASES_ACTIVAS_DEFAULT
    # preserva el ORDEN de CLASES_CABINA (economy siempre primero cuando está
    # activa — define precio_base/predicciones, debe resolverse antes que
    # business/first en el loop de abajo), filtrando por lo que el admin dejó activo
    activas = {c.strip() for c in valor.split(",") if c.strip()}
    return tuple(c for c in CLASES_CABINA if c in activas)


async def enriquecer_con_google_flights(
    client: GoogleFlightsClient,
    hoy: datetime.date | None = None,
    rutas: list[tuple[str, str]] | None = None,
    clases: tuple[str, ...] | None = None,
) -> dict:
    repo = VuelosRepository()
    hoy = hoy or datetime.date.today()
    clases = clases if clases is not None else await _clases_activas(repo)

    if rutas is None:
        valor_corrida = await repo.config("vuelos.google_flights_rutas_por_corrida")
        rutas_por_corrida = int(valor_corrida) if valor_corrida else RUTAS_POR_CORRIDA_DEFAULT
        pares = await repo.rutas_disponibles()
        universo_str = [f"{o}|{d}" for o, d in pares]
        seleccion_str = rebanada_rotativa(universo_str, rutas_por_corrida, hoy)
        rutas = [tuple(s.split("|")) for s in seleccion_str]

    fuente = await repo.fuente_por_nombre("Google Flights (SerpApi)")
    nivel_premium = await repo.nivel_tarifa_por_nombre(NIVEL_PREMIUM_NOMBRE)
    fecha_inicio = _ahora_iso()
    procesados = actualizados = 0
    error_detalle = None
    motivo_parcial = None

    try:
        for origen, destino in rutas:
            candidatos: list[dict] | None = None
            for clase in clases:
                if fuente and not await hay_cupo(
                    fuente["id"], fuente.get("cuota_mensual_estimada"), getattr(client, "llamadas_realizadas", 0)
                ):
                    motivo_parcial = "cuota_mensual_agotada"
                    break

                procesados += 1
                resultado = await client.buscar(origen, destino, hoy.isoformat(), clase=clase)
                if resultado is None:
                    continue

                if candidatos is None:
                    candidatos = await repo.buscar(origen, destino, hoy.isoformat())
                if not candidatos:
                    continue
                por_numero = {v["numero_vuelo"]: v for v in candidatos}

                for vuelo_real in resultado["vuelos"]:
                    # Empareja por número de vuelo si AeroDataBox ya lo puso
                    # real; si no matchea ninguno, usa el primer candidato de
                    # la ruta como aproximación (el precio es real, puede no
                    # ser el de ESE vuelo exacto — documentado, no inventado).
                    vuelo_existente = por_numero.get(vuelo_real["numero_vuelo"]) or candidatos[0]

                    if clase == "economy":
                        # precio_base/emisiones/detalles del vuelo en sí solo
                        # los define la clase base — business/first solo
                        # aportan el precio de SU propia tarifa, más abajo.
                        cambios = {"precio_base": vuelo_real["precio"]}
                        if vuelo_real["emisiones_co2_kg"] is not None:
                            cambios["emisiones_co2_kg"] = vuelo_real["emisiones_co2_kg"]
                        if vuelo_real["fuente_busqueda_ref"]:
                            cambios["fuente_busqueda_ref"] = vuelo_real["fuente_busqueda_ref"]
                        if vuelo_real["detalles_extra"]:
                            cambios["detalles_extra"] = vuelo_real["detalles_extra"]
                        await repo.actualizar_vuelo(vuelo_existente["id"], cambios)

                    if vuelo_real["precio"] is not None:
                        tarifa = await repo.tarifa_por_vuelo_y_clase(vuelo_existente["id"], clase)
                        if tarifa:
                            await repo.actualizar_tarifa(tarifa["id"], {"precio_final": vuelo_real["precio"]})
                        elif clase != "economy" and nivel_premium:
                            # Primera vez que esta ruta/vuelo trae precio real
                            # de cabina premium — economy siempre viene
                            # sembrada por el catálogo base, nunca se crea acá.
                            await repo.crear_tarifa(
                                {
                                    "vuelo_id": vuelo_existente["id"],
                                    "nivel_tarifa_id": nivel_premium["id"],
                                    "clase_cabina": clase,
                                    "precio_final": vuelo_real["precio"],
                                    "cupos_disponibles": CUPOS_PREMIUM_DEFAULT.get(clase, 8),
                                }
                            )

                    actualizados += 1
                    break  # un solo vuelo real emparejado por ruta/clase y corrida

                # price_insights viene en la misma respuesta que economy —
                # no tiene desglose por clase, así que solo se guarda una vez.
                if clase == "economy" and resultado["predicciones"]:
                    p = resultado["predicciones"]
                    rango_min, rango_max = p["rango_tipico_min"], p["rango_tipico_max"]
                    # `precio_predicho`/`tendencia`/`confianza` NO vienen de la
                    # API — es una heurística propia simple sobre price_insights
                    # (dbml v3 lo documenta así explícitamente, no un modelo real).
                    precio_predicho = (
                        (rango_min + rango_max) / 2
                        if rango_min is not None and rango_max is not None
                        else p["precio_minimo_historico"]
                    )
                    data_prediccion = {
                        "origen_codigo": origen,
                        "destino_codigo": destino,
                        "fecha_objetivo": hoy.isoformat(),
                        "precio_minimo_historico": p["precio_minimo_historico"],
                        "nivel_precio": p["nivel_precio"],
                        "rango_tipico_min": rango_min,
                        "rango_tipico_max": rango_max,
                        "historico_precios": p["historico_precios"],
                        "precio_predicho": precio_predicho or 0.0,
                        "tendencia": _NIVEL_A_TENDENCIA.get(p["nivel_precio"], "estable"),
                        "confianza": 0.6,
                        "fecha_calculo": _ahora_iso(),
                    }
                    existente = await repo.prediccion_por_ruta_fecha(origen, destino, hoy.isoformat())
                    if existente:
                        await repo.actualizar_prediccion(existente["id"], data_prediccion)
                    else:
                        await repo.crear_prediccion(data_prediccion)
            else:
                continue  # el for clase no se cortó por cuota -> seguir con la próxima ruta
            break  # se cortó por cuota agotada -> no seguir con más rutas tampoco

        estado = "exitoso" if actualizados > 0 else "parcial"
    except Exception as exc:  # noqa: BLE001 — se registra en la bitácora, no se oculta
        estado = "fallido"
        error_detalle = str(exc)

    if fuente:
        await repo.crear_log_sincronizacion(
            {
                "fuente_id": fuente["id"],
                "tipo_producto": "vuelo",
                "fecha_inicio": fecha_inicio,
                "fecha_fin": _ahora_iso(),
                "estado": estado,
                "registros_procesados": procesados,
                "registros_nuevos": 0,
                "registros_actualizados": actualizados,
                "unidades_cuota_consumidas": getattr(client, "llamadas_realizadas", 0),
                "error_detalle": error_detalle,
            }
        )

    resumen = {"rutas": rutas, "procesados": procesados, "actualizados": actualizados, "estado": estado}
    if motivo_parcial:
        resumen["motivo_parcial"] = motivo_parcial
    if error_detalle:
        resumen["error_detalle"] = error_detalle
    print(f"[VUELOS-GOOGLEFLIGHTS] {resumen}")
    return resumen
