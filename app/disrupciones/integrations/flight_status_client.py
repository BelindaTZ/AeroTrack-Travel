"""RF-DIS-001 (CU-O27) — única puerta a la API real de estado de vuelo
(REG-F1/I7). `AviationStackClient` es la implementación concreta; el resto
del sistema solo depende de la interfaz abstracta `FlightStatusClient`, así
que la fuente es reemplazable sin tocar servicios (y sustituible por un
doble de prueba determinístico en tests, sin gastar la cuota real).
"""

import abc
import asyncio
import logging

import httpx

from app.shared.pocketbase_client import get_pocketbase_client

logger = logging.getLogger("disrupciones.flight_status")

# Vocabulario normalizado que consume el resto del sistema — no el crudo de
# AviationStack (`flight_status`: scheduled/active/landed/cancelled/incident/
# diverted), que se traduce aquí, en el único punto que conoce ese formato.
ESTADOS_NORMALIZADOS = {"programado", "retrasado", "cancelado", "desviado", "completado"}


class FlightStatusClient(abc.ABC):
    @abc.abstractmethod
    async def esta_disponible(self) -> bool:
        """RNF-DIS-001 — chequeo barato antes de gastar cuota en la consulta real."""

    @abc.abstractmethod
    async def consultar_estado(self, numero_vuelo: str, fecha: str) -> dict | None:
        """Retorna `{"estado_api", "retraso_minutos", "nueva_hora_llegada"}` o
        `None` si la API no tiene datos para ese vuelo/fecha (respuesta real
        vacía, no una falla)."""


def _normalizar_estado(flight_status: str, retraso_minutos: int | None) -> str:
    mapa = {
        "cancelled": "cancelado",
        "diverted": "desviado",
        "landed": "completado",
    }
    if flight_status in mapa:
        return mapa[flight_status]
    if retraso_minutos and retraso_minutos > 0:
        return "retrasado"
    return "programado"


class AviationStackClient(FlightStatusClient):
    """Implementación real sobre https://api.aviationstack.com (REG-I7)."""

    _BASE_URL = "https://api.aviationstack.com/v1"

    async def _config(self) -> dict:
        client = get_pocketbase_client()
        claves = [
            "api_estado_vuelo.api_key",
            "api_estado_vuelo.timeout_segundos",
            "api_estado_vuelo.limite_mensual",
            "api_estado_vuelo.llamadas_usadas_mes",
            "api_estado_vuelo.periodo_actual",
        ]
        valores = {}
        for clave in claves:
            registro = await client.get_first("configuracion_sistema", f'clave="{clave}"')
            if registro is None:
                raise RuntimeError(f"configuracion_sistema.{clave} no está sembrado")
            valores[clave] = registro["valor"]
        return valores

    async def esta_disponible(self) -> bool:
        # RNF-DIS-001: si ya se agotó la cuota mensual configurada, la API
        # se considera no disponible sin siquiera intentar la llamada —
        # evita gastar la última cuota real en una consulta que igual
        # fallaría (429) y deja rastro claro de degradación por cuota.
        try:
            config = await self._config()
        except RuntimeError:
            return False
        try:
            usadas = int(config["api_estado_vuelo.llamadas_usadas_mes"])
            limite = int(config["api_estado_vuelo.limite_mensual"])
        except (KeyError, ValueError):
            return True
        return usadas < limite

    async def consultar_estado(self, numero_vuelo: str, fecha: str) -> dict | None:
        config = await self._config()
        timeout = float(config["api_estado_vuelo.timeout_segundos"])
        api_key = config["api_estado_vuelo.api_key"]

        try:
            datos = await asyncio.wait_for(
                self._consultar_sync_wrapper(api_key, numero_vuelo, timeout), timeout=timeout + 2
            )
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.warning("AviationStack no respondió para %s: %s", numero_vuelo, exc)
            raise

        await self._incrementar_contador(config)

        vuelos = datos.get("data") or []
        if not vuelos:
            return None

        vuelo = vuelos[0]
        salida = vuelo.get("departure") or {}
        retraso_minutos = salida.get("delay")
        flight_status = vuelo.get("flight_status") or "scheduled"
        estado_api = _normalizar_estado(flight_status, retraso_minutos)
        return {
            "estado_api": estado_api,
            "retraso_minutos": retraso_minutos,
            "nueva_hora_llegada": (vuelo.get("arrival") or {}).get("estimated"),
        }

    async def _consultar_sync_wrapper(self, api_key: str, numero_vuelo: str, timeout: float) -> dict:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                f"{self._BASE_URL}/flights",
                params={"access_key": api_key, "flight_iata": numero_vuelo},
            )
            resp.raise_for_status()
            return resp.json()

    async def _incrementar_contador(self, config: dict) -> None:
        client = get_pocketbase_client()
        registro = await client.get_first(
            "configuracion_sistema", 'clave="api_estado_vuelo.llamadas_usadas_mes"'
        )
        nuevas = int(config["api_estado_vuelo.llamadas_usadas_mes"]) + 1
        await client.update_record("configuracion_sistema", registro["id"], {"valor": str(nuevas)})
