"""RF-ACT-004,005 (CU-O120) — única puerta a Travel Advisor (REG-F1).
Reemplazo confirmado de Viator (roto). El resto del sistema depende de la
interfaz abstracta `TravelAdvisorClient`, no del proveedor concreto.

Flujo real confirmado en vivo 2026-07-19 (campos verificados ANTES de
escribir la extracción, a diferencia de Hoteles/Autos donde se corrigieron
después de un primer intento fallido — ver errores-conocidos.md):
  1. `GET locations/v2/auto-complete?query={ciudad}` ->
     `data.Typeahead_autocomplete.results[0].detailsV2.locationId` (geoId).
  2. `POST attraction-products/v2/list` body `{"geoId":..., "currencyCode":"USD"}`
     -> `data.AppPresentation_queryAppListV2[0].sections[].listSingleCardContent`,
     cada card con `trackingKey` (string JSON: `prc`/`cur`/`lid`/`br`/`rc`)
     y `primaryInfo.text` (categoría específica, ej. "Sightseeing Cruises" —
     más específica que `category.name` del detalle, "Activity").
  3. `GET attractions/get-details?location_id={lid}&currency=USD&lang=en_US`
     (legacy — el `v2/get-details` está confirmado roto, 204 vacío) ->
     `name` (limpio, sin el prefijo "N. " que sí trae el `cardTitle` del
     paso 2), `description`, `rating`, `num_reviews`, `address_obj.city`/
     `.country`, `category.name`, `reviews[]` ya embebidas (`author`,
     `rating`, `summary`, `published_date` ISO real — no texto relativo
     como en Hoteles).
"""

import abc
import json

import httpx


class TravelAdvisorClient(abc.ABC):
    @abc.abstractmethod
    async def resolver_geo_id(self, ciudad: str) -> int | None:
        """Paso 1."""

    @abc.abstractmethod
    async def buscar_actividades(self, geo_id: int) -> list[dict]:
        """Paso 2. Cada card trae `trackingKey` (JSON string) y
        `primaryInfo.text`/`cardPhoto` — `catalogo_service.py` interpreta."""

    @abc.abstractmethod
    async def obtener_detalle(self, content_id: str) -> dict:
        """Paso 3. Trae reseñas embebidas en `reviews[]`."""


def parsear_tracking_key(tracking_key: str | None) -> dict:
    if not tracking_key:
        return {}
    try:
        return json.loads(tracking_key)
    except (TypeError, ValueError):
        return {}


class TravelAdvisorApiClient(TravelAdvisorClient):
    """Implementación real sobre RapidAPI (host `travel-advisor.p.rapidapi.com`)."""

    _BASE_URL = "https://travel-advisor.p.rapidapi.com"

    def __init__(self, api_key: str, api_host: str, timeout: float = 15.0) -> None:
        self._api_key = api_key
        self._api_host = api_host
        self._timeout = timeout
        self.llamadas_realizadas = 0

    def _headers(self) -> dict:
        return {"x-rapidapi-key": self._api_key, "x-rapidapi-host": self._api_host}

    async def resolver_geo_id(self, ciudad: str) -> int | None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._BASE_URL}/locations/v2/auto-complete",
                params={"query": ciudad},
                headers=self._headers(),
            )
            self.llamadas_realizadas += 1
            resp.raise_for_status()
            datos = resp.json()

        resultados = ((datos.get("data") or {}).get("Typeahead_autocomplete") or {}).get("results") or []
        if not resultados:
            return None
        return (resultados[0].get("detailsV2") or {}).get("locationId")

    async def buscar_actividades(self, geo_id: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._BASE_URL}/attraction-products/v2/list",
                json={"geoId": geo_id, "currencyCode": "USD"},
                headers={**self._headers(), "content-type": "application/json"},
            )
            self.llamadas_realizadas += 1
            resp.raise_for_status()
            datos = resp.json()

        listados = (datos.get("data") or {}).get("AppPresentation_queryAppListV2") or []
        if not listados:
            return []
        secciones = listados[0].get("sections") or []
        return [s["listSingleCardContent"] for s in secciones if s.get("listSingleCardContent")]

    async def obtener_detalle(self, content_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._BASE_URL}/attractions/get-details",
                params={"location_id": content_id, "currency": "USD", "lang": "en_US"},
                headers=self._headers(),
            )
            self.llamadas_realizadas += 1
            resp.raise_for_status()
            return resp.json()
