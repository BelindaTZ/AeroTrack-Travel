"""RF-HOT-004 (CU-O118) — única puerta a HotelLens (REG-F1). El resto del
sistema depende de la interfaz abstracta `HotelLensClient`, no del
proveedor concreto — reemplazable, y sustituible por un doble determinista
en tests (mismo patrón que `FlightStatusClient` en Disrupciones).

Flujo real confirmado (docs/apis-reference.md sección 5,
docs/aerotrack-travel-propuesta-tablas-v3.dbml, nota del módulo Hoteles):
  1. `GET /api/v1/hotels?location=` (Google Hotels, descubrimiento)
  2. `GET /api/v1/hotels/prices?url=` (comparador de OTAs — extrae el
     hotel_id real de Booking.com del `booking_url`)
  3. `GET /api/v1/booking/hotels/details?hotel_id=&check_in=&check_out=`
     (fuente primaria real: room_offers[], ciudad limpia, amenidades)
  Reseñas: `GET /api/v1/hotels/reviews?url=` (mismo `url` del paso 1).

⚠️ Plan BASIC de HotelLens: rate limit estricto (~4-5 llamadas/min, 429 si
se excede, se recupera en ~60s) — `catalogo_service.py` es quien controla
cuántos hoteles resolver en detalle por corrida. Este cliente sí espacia sus
propias llamadas (`_DELAY_ENTRE_LLAMADAS`) porque una corrida ampliada (más
ciudades/hoteles por corrida) hace casi seguro pegarle al 429 sin espaciar;
no reintenta ni hace backoff progresivo (mantenerlo simple; una corrida
fallida por 429 se ve en `sincronizaciones_log` y se reintenta en el
próximo ciclo). También cuenta sus llamadas reales en `llamadas_realizadas`
para que `catalogo_service.py` audite el consumo real en
`sincronizaciones_log.unidades_cuota_consumidas`.
"""

import abc
import asyncio
import re

import httpx

_HOTEL_ID_BOOKING_RE = re.compile(r"[?&](?:dest_id|highlighted_hotels)=(\d+)")


class HotelLensClient(abc.ABC):
    @abc.abstractmethod
    async def buscar_hoteles(self, ciudad: str) -> list[dict]:
        """Paso 1. Cada item trae al menos `name`/`url` (entidad Google)."""

    @abc.abstractmethod
    async def obtener_ofertas(self, url_entidad: str) -> list[dict]:
        """Paso 2. Cada oferta trae `booking_url` (y las de otros OTAs)."""

    @abc.abstractmethod
    async def obtener_detalle_booking(self, hotel_id_booking: str, check_in: str, check_out: str) -> dict:
        """Paso 3. Trae `city`, `amenities`, `room_offers[]` reales."""

    @abc.abstractmethod
    async def obtener_resenas(self, url_entidad: str) -> list[dict]:
        """Reseñas cacheadas junto con el catálogo (RF-HOT-005)."""


def extraer_hotel_id_booking(booking_url: str) -> str | None:
    """Booking.com embebe su hotel_id en la query string del `booking_url`
    real que trae `/hotels/prices` — ver nota del módulo en el dbml v3,
    ejemplo confirmado: `dest_id=721193&highlighted_hotels=721193&...`."""
    match = _HOTEL_ID_BOOKING_RE.search(booking_url)
    return match.group(1) if match else None


class HotelLensApiClient(HotelLensClient):
    """Implementación real sobre RapidAPI (host `hotellens.p.rapidapi.com`)."""

    _BASE_URL = "https://hotellens.p.rapidapi.com"
    _DELAY_ENTRE_LLAMADAS = 13.0  # segundos — respeta el rate limit BASIC (~4-5 llamadas/min)

    def __init__(self, api_key: str, api_host: str, timeout: float = 15.0) -> None:
        self._api_key = api_key
        self._api_host = api_host
        self._timeout = timeout
        self.llamadas_realizadas = 0

    def _headers(self) -> dict:
        return {"x-rapidapi-key": self._api_key, "x-rapidapi-host": self._api_host}

    async def _get(self, path: str, params: dict) -> dict:
        if self.llamadas_realizadas > 0:
            await asyncio.sleep(self._DELAY_ENTRE_LLAMADAS)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._BASE_URL}{path}", params=params, headers=self._headers())
            self.llamadas_realizadas += 1
            resp.raise_for_status()
            return resp.json()

    async def buscar_hoteles(self, ciudad: str) -> list[dict]:
        datos = await self._get("/api/v1/hotels", {"location": ciudad})
        return datos if isinstance(datos, list) else datos.get("hotels") or datos.get("data") or []

    async def obtener_ofertas(self, url_entidad: str) -> list[dict]:
        # Confirmado en vivo 2026-07-19: la respuesta real es un objeto con
        # `offers[]` (no una lista plana ni `.data`/`.prices`) — cada oferta
        # trae `provider`/`booking_url` real, ej. la de Booking.com incluye
        # literal `dest_id=54642&highlighted_hotels=54642` en la query string.
        datos = await self._get("/api/v1/hotels/prices", {"url": url_entidad})
        return datos.get("offers") or []

    async def obtener_detalle_booking(self, hotel_id_booking: str, check_in: str, check_out: str) -> dict:
        return await self._get(
            "/api/v1/booking/hotels/details",
            {"hotel_id": hotel_id_booking, "check_in": check_in, "check_out": check_out},
        )

    async def obtener_resenas(self, url_entidad: str) -> list[dict]:
        datos = await self._get("/api/v1/hotels/reviews", {"url": url_entidad})
        return datos if isinstance(datos, list) else datos.get("reviews") or datos.get("data") or []
