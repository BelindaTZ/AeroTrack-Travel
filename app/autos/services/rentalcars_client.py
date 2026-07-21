"""RF-AUT-004 (CU-O119) — única puerta a Global Rental Cars (REG-F1). El
resto del sistema depende de la interfaz abstracta `RentalCarsClient`, no
del proveedor concreto — reemplazable, y sustituible por un doble
determinista en tests (mismo patrón que `FlightStatusClient`/
`HotelLensClient`).

Solo se implementa el sub-proveedor **Expedia** (RF-AUT-004: "priorizando
Expedia cuando esté disponible" — es el único de los tres sin el bug de
RN-AUT-001 de ignorar fecha/ubicación pedida, confirmado en
docs/apis-reference.md sección 8). Priceline/Booking quedan documentados
como fuente secundaria futura, no implementados en esta fase.

Flujo real confirmado en vivo 2026-07-19 (la respuesta real es un árbol de
"cards" tipo GraphQL, no el JSON plano que sugería la doc previa a esta
verificación — ver `errores-conocidos.md`):
  1. `GET /1.0/expedia/cars/auto-complete?query={ciudad}` -> código IATA
     en `data[0].hierarchyInfo.airport.airportCode`.
  2. `GET /1.0/expedia/cars/search?pickUpLocation={codigo}` ->
     `data.carSearchResults.carSearchListings[]`, cada card con
     `vehicle.category`/`.description`/`.attributes[]` (transmisión vía el
     attribute con `icon.id="transmission"`), `vendor.image.description`
     (nombre de la rentadora), `priceSummary.lead.formattedValue` ("$63"),
     `detailsContext.carOfferToken` (para revalidar en RF-AUT-005, no usado
     en esta fase de catálogo).
"""

import abc
import re

import httpx

_PRECIO_RE = re.compile(r"[\d,.]+")


class RentalCarsClient(abc.ABC):
    @abc.abstractmethod
    async def resolver_codigo_ciudad(self, ciudad: str) -> str | None:
        """Código IATA/aeropuerto que usa `buscar_autos`, o None si la
        ciudad no se pudo resolver."""

    @abc.abstractmethod
    async def buscar_autos(self, codigo_ciudad: str) -> list[dict]:
        """Cards de oferta reales tal como las devuelve el proveedor —
        `catalogo_service.py` es quien las interpreta/normaliza."""


def parsear_precio(formatted_value: str | None) -> float | None:
    """"$63" -> 63.0. None/vacío -> None (no fabricar un precio)."""
    if not formatted_value:
        return None
    match = _PRECIO_RE.search(formatted_value)
    return float(match.group().replace(",", "")) if match else None


def extraer_transmision(attributes: list[dict]) -> str | None:
    for attr in attributes or []:
        if (attr.get("icon") or {}).get("id") == "transmission":
            return attr.get("text")
    return None


class RentalCarsApiClient(RentalCarsClient):
    """Implementación real sobre RapidAPI (host
    `global-rental-cars.p.rapidapi.com`), sub-proveedor Expedia."""

    _BASE_URL = "https://global-rental-cars.p.rapidapi.com"

    def __init__(self, api_key: str, api_host: str, timeout: float = 20.0) -> None:
        self._api_key = api_key
        self._api_host = api_host
        self._timeout = timeout
        self.llamadas_realizadas = 0

    def _headers(self) -> dict:
        return {"x-rapidapi-key": self._api_key, "x-rapidapi-host": self._api_host}

    async def _get(self, path: str, params: dict) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._BASE_URL}{path}", params=params, headers=self._headers())
            self.llamadas_realizadas += 1
            resp.raise_for_status()
            return resp.json()

    async def resolver_codigo_ciudad(self, ciudad: str) -> str | None:
        datos = await self._get("/1.0/expedia/cars/auto-complete", {"query": ciudad})
        resultados = datos.get("data") or []
        if not resultados:
            return None
        return ((resultados[0].get("hierarchyInfo") or {}).get("airport") or {}).get("airportCode")

    async def buscar_autos(self, codigo_ciudad: str) -> list[dict]:
        datos = await self._get("/1.0/expedia/cars/search", {"pickUpLocation": codigo_ciudad})
        car_search_results = ((datos.get("data") or {}).get("carSearchResults")) or {}
        return car_search_results.get("carSearchListings") or []
