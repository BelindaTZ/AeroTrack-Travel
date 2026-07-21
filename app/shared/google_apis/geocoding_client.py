"""Única puerta a la Geocoding API CLÁSICA de Google Cloud
(`/maps/api/geocode/json`, no la variante "New"/v4) — decisión deliberada:
la clásica no tiene límite diario configurado (solo 3,000/min), mientras
que la variante nueva (GeocodeAddress/Location/Place) sí tiene 100/día
(Cuotas y Límites → IAM, 2026-07-20) sin que necesitemos sus campos extra.
Por eso este cliente no gatea con `cuota_service` — no hay techo diario
real que proteger en el endpoint que usamos.

Sin UI conectada todavía en este alcance — queda como complemento de
Places (resolver coordenadas de un lugar elegido) para cuando haga falta.
"""

import abc

import httpx


class GeocodingClient(abc.ABC):
    @abc.abstractmethod
    async def geocodificar(self, direccion: str) -> dict | None:
        """`{"direccion_formateada", "lat", "lng"}` o None si Google no
        resolvió ninguna coincidencia."""


class GeocodingApiClient(GeocodingClient):
    """Implementación real sobre `maps.googleapis.com/maps/api/geocode`
    (endpoint clásico, sin límite diario configurado)."""

    _BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def geocodificar(self, direccion: str) -> dict | None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(self._BASE_URL, params={"address": direccion, "key": self._api_key})
            resp.raise_for_status()
            datos = resp.json()

        resultados = datos.get("results") or []
        if not resultados:
            return None
        primero = resultados[0]
        ubicacion = (primero.get("geometry") or {}).get("location") or {}
        return {
            "direccion_formateada": primero.get("formatted_address"),
            "lat": ubicacion.get("lat"),
            "lng": ubicacion.get("lng"),
        }
