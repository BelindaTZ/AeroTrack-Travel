"""RF-CRU-005 (CU-O122) — única puerta a Cruise Pricing API (REG-F1). El
resto del sistema depende de la interfaz abstracta `CruisePricingClient`,
no del proveedor concreto.

Campos reales confirmados en vivo 2026-07-19 (verificados ANTES de escribir
la extracción, mismo criterio que Actividades):
  - `GET /cruise-lines` -> `data[]` con `company` (slug), `display_name`,
    `destinations[]`.
  - `GET /cruises?limit=` -> `data[]` con `cruise_id`, `company`,
    `ship_name`, `departure_date`, `duration`, `price`, `currency`,
    `ports_list[]` ({"port","day"}).
  - `GET /cruises/{id}` -> mismo shape + `cabin_prices_per_person`
    (dict `{"INTERIOR": 700, "BALCONY": ...}` — precio REAL por tipo de
    camarote). **Confirmado (de nuevo) que NO existe ningún campo de
    inventario/disponibilidad en toda la respuesta** — mismo gap que
    Actividades, `cupos_disponibles` es regla de negocio (RF-CRU-006).
"""

import abc

import httpx


class CruisePricingClient(abc.ABC):
    @abc.abstractmethod
    async def listar_navieras(self) -> list[dict]:
        """`/cruise-lines` — 9 navieras conocidas, cuota barata."""

    @abc.abstractmethod
    async def buscar_cruceros(self, limite: int) -> list[dict]:
        """`/cruises?limit=` — resumen de cruceros reales."""

    @abc.abstractmethod
    async def obtener_detalle(self, cruise_id: str) -> dict:
        """`/cruises/{id}` — trae `cabin_prices_per_person` real."""


class CruisePricingApiClient(CruisePricingClient):
    """Implementación real sobre RapidAPI (host
    `cruise-pricing-api1.p.rapidapi.com`)."""

    _BASE_URL = "https://cruise-pricing-api1.p.rapidapi.com"

    def __init__(self, api_key: str, api_host: str, timeout: float = 15.0) -> None:
        self._api_key = api_key
        self._api_host = api_host
        self._timeout = timeout
        self.llamadas_realizadas = 0

    def _headers(self) -> dict:
        return {"x-rapidapi-key": self._api_key, "x-rapidapi-host": self._api_host}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._BASE_URL}{path}", params=params or {}, headers=self._headers())
            self.llamadas_realizadas += 1
            resp.raise_for_status()
            return resp.json()

    async def listar_navieras(self) -> list[dict]:
        datos = await self._get("/cruise-lines")
        return datos.get("data") or []

    async def buscar_cruceros(self, limite: int) -> list[dict]:
        datos = await self._get("/cruises", {"limit": limite})
        return datos.get("data") or []

    async def obtener_detalle(self, cruise_id: str) -> dict:
        datos = await self._get(f"/cruises/{cruise_id}")
        return datos.get("data") or {}
