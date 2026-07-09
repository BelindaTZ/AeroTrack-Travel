"""
AeroTrack Travel — Proveedor de estado de vuelo en tiempo real (CU-O40)
==========================================================================
Principio F1 de la constitución: ninguna funcionalidad se acopla
directamente a un proveedor específico sin una capa de abstracción que
permita sustituirlo. Este módulo expone una única función pública,
`consultar_estado_vuelo()`, que resuelve el proveedor activo leyendo
`configuracion_sistema` (NO variables de entorno directamente — eso es
lo que permite cambiar de proveedor o rotar la API key desde la UI sin
tocar .env ni redeployar, CU-O17).

Proveedor implementado: AviationStack (plan gratuito). Para agregar
AeroDataBox más adelante, basta con implementar otra función con la
misma firma y registrarla en PROVEEDORES.
"""

from __future__ import annotations

import datetime
import time

import requests

import pocketbase_client as pb

_CATEGORIA = "api_estado_vuelo"


def _config(clave: str, default: str | None = None) -> str | None:
    return pb.get_config(f"{_CATEGORIA}.{clave}", default)


def _registro(clave: str):
    return pb.get_first("configuracion_sistema", f'clave="{_CATEGORIA}.{clave}"')


def _estado_cuota() -> dict:
    """Lee límite/contador/periodo. Si el mes cambió desde la última
    llamada, resetea el contador a 0 (rotación mensual, free tier de
    AviationStack). Si el control de cuota no está configurado todavía,
    no bloquea nada (comportamiento previo, sin límite)."""
    rec_usadas = _registro("llamadas_usadas_mes")
    rec_limite = _registro("limite_mensual")
    rec_periodo = _registro("periodo_actual")
    if not (rec_usadas and rec_limite and rec_periodo):
        return {"limite": None, "usadas": 0, "rec_usadas_id": None}

    periodo_hoy = datetime.datetime.utcnow().strftime("%Y-%m")
    usadas = int(rec_usadas["valor"])
    limite = int(rec_limite["valor"])

    if rec_periodo["valor"] != periodo_hoy:
        usadas = 0
        pb.update("configuracion_sistema", rec_usadas["id"], {"valor": "0"})
        pb.update("configuracion_sistema", rec_periodo["id"], {"valor": periodo_hoy})
        print(f"[FLIGHT-STATUS] contador mensual reseteado (nuevo periodo {periodo_hoy})")

    return {"limite": limite, "usadas": usadas, "rec_usadas_id": rec_usadas["id"]}


def _incrementar_contador(rec_usadas_id: str, usadas_actual: int) -> None:
    pb.update("configuracion_sistema", rec_usadas_id, {"valor": str(usadas_actual + 1)})


def _respaldo_simulador(numero_vuelo: str) -> dict:
    """Principio E3: si no hay cupo para consultar el proveedor real, el
    sistema sigue operando con la fuente estadística como respaldo — nunca
    falla silenciosamente. numero_vuelo[:2] asume el formato IATA estándar
    (2 caracteres de aerolínea + número), consistente con el catálogo."""
    from disrupciones_tasks import _otp_por_aerolinea

    iata = numero_vuelo[:2]
    otp = _otp_por_aerolinea().get(iata)
    base = {
        "encontrado": otp is not None,
        "proveedor": "simulador_fallback",
        "numero_vuelo": numero_vuelo,
        "motivo_fallback": "cuota_api_agotada",
    }
    if otp is None:
        return base
    riesgo = round(100 - otp, 2)
    return {
        **base,
        "estado_raw": "riesgo_estimado",
        "cancelado": False,
        "desviado": False,
        "retraso_min": None,
        "probabilidad_riesgo_simulada": riesgo,
    }


def _consultar_aviationstack(numero_vuelo: str, timeout: int, max_reintentos: int) -> dict:
    api_key = _config("api_key")
    if not api_key:
        raise RuntimeError("api_estado_vuelo.api_key no está configurado en configuracion_sistema")

    url = "http://api.aviationstack.com/v1/flights"
    params = {"access_key": api_key, "flight_iata": numero_vuelo}

    ultimo_error: Exception | None = None
    for intento in range(max_reintentos):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.RequestException as exc:
            ultimo_error = exc
            time.sleep(1 * (intento + 1))
    else:
        raise RuntimeError(f"AviationStack no respondió tras {max_reintentos} intentos: {ultimo_error}")

    if "error" in data:
        raise RuntimeError(f"AviationStack devolvió error: {data['error']}")

    vuelos = data.get("data", [])
    if not vuelos:
        return {"encontrado": False, "proveedor": "aviationstack", "numero_vuelo": numero_vuelo}

    v = vuelos[0]
    estado_raw = v.get("flight_status")  # scheduled | active | landed | cancelled | incident | diverted
    salida = v.get("departure", {})
    return {
        "encontrado": True,
        "proveedor": "aviationstack",
        "numero_vuelo": numero_vuelo,
        "estado_raw": estado_raw,
        "cancelado": estado_raw == "cancelled",
        "desviado": estado_raw == "diverted",
        "retraso_min": salida.get("delay"),
        "aeropuerto_salida": salida.get("iata"),
        "hora_salida_programada": salida.get("scheduled"),
        "hora_salida_estimada": salida.get("estimated"),
    }


PROVEEDORES = {
    "aviationstack": _consultar_aviationstack,
}


def consultar_estado_vuelo(numero_vuelo: str) -> dict:
    """Punto de entrada único (F1). Resuelve el proveedor activo y los
    timeouts/reintentos (F2) desde configuracion_sistema en cada llamada,
    para que un cambio en la UI aplique sin reiniciar el DAG.

    Antes de llamar al proveedor real, verifica la cuota mensual
    (api_estado_vuelo.limite_mensual vs .llamadas_usadas_mes). Si ya se
    alcanzó, degrada al simulador estadístico (E3) en vez de fallar o de
    seguir gastando cuota — se registra explícitamente que la degradación
    fue por cuota, no por una falla del servicio externo."""
    cuota = _estado_cuota()
    if cuota["limite"] is not None and cuota["usadas"] >= cuota["limite"]:
        print(f"[FLIGHT-STATUS] cuota mensual agotada ({cuota['usadas']}/{cuota['limite']}) — "
              f"degradando a simulador estadístico (E3). NO es una falla de AviationStack.")
        return _respaldo_simulador(numero_vuelo)

    proveedor = _config("proveedor", "aviationstack")
    timeout = int(_config("timeout_segundos", "10"))
    max_reintentos = int(_config("max_reintentos", "2"))

    fn = PROVEEDORES.get(proveedor)
    if not fn:
        raise RuntimeError(f"Proveedor de estado de vuelo no soportado: {proveedor}")

    resultado = fn(numero_vuelo, timeout, max_reintentos)

    if cuota["limite"] is not None:
        _incrementar_contador(cuota["rec_usadas_id"], cuota["usadas"])
        print(f"[FLIGHT-STATUS] cuota: {cuota['usadas'] + 1}/{cuota['limite']} llamadas usadas este mes")

    return resultado
