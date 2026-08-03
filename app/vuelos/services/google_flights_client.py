"""Única puerta a Google Flights vía SerpApi (REG-F1) — no confundir con
la marca "Google Cloud APIS" de `.env` (Places/Maps/Routes), esta es una
cuenta aparte en serpapi.com. El resto del sistema depende de la interfaz
abstracta `GoogleFlightsClient`, no del proveedor concreto.

Flujo real confirmado (docs/google-flights-serpapi-hallazgos.md):
`engine=google_flights`, `departure_id`/`arrival_id`/`outbound_date`,
`travel_class` (2=Premium Economy, 3=Business, 4=First; se omite para
Economy). Cuota real: 250 búsquedas/mes compartidas entre 3 engines de
SerpApi, este proyecto solo usa `google_flights`.

⚠️ Gotcha real confirmado (mismo doc, líneas 77-100): con `travel_class=4`
SerpApi puede devolver una ruta DISTINTA a la pedida con
`"status": "Success"`, sin ningún aviso en la respuesta (probado: pedir
ATL→JFK devolvió ATL→DCA). `_ruta_coincide()` es la única defensa —
nunca se persiste un itinerario sin pasar por ahí primero.

Solo se consideran itinerarios de un solo tramo (`len(flights) == 1`):
el modelo de datos del proyecto (`vuelos_catalogo`) no tiene concepto de
escalas, así que un itinerario con conexión no tiene con qué vuelo
sintético/AeroDataBox emparejar.
"""

import abc
import re

import httpx

_ESPACIO_NUMERO_VUELO = re.compile(r"\s+")

_CLASE_A_TRAVEL_CLASS = {"premium_economy": 2, "business": 3, "first": 4}  # economy: sin param, default de la API


def normalizar_numero_vuelo(numero: str) -> str:
    return _ESPACIO_NUMERO_VUELO.sub("", numero or "")


def _ruta_coincide(itinerario: dict, origen: str, destino: str) -> bool:
    tramos = itinerario.get("flights") or []
    if len(tramos) != 1:
        return False
    tramo = tramos[0]
    origen_real = (tramo.get("departure_airport") or {}).get("id")
    destino_real = (tramo.get("arrival_airport") or {}).get("id")
    return origen_real == origen and destino_real == destino


class GoogleFlightsClient(abc.ABC):
    @abc.abstractmethod
    async def buscar(self, origen: str, destino: str, fecha: str, clase: str = "economy") -> dict | None:
        """`None` si SerpApi no trajo ningún itinerario directo real que
        coincida con la ruta pedida. Si hay resultados:
        `{"vuelos": [{"numero_vuelo", "precio", "emisiones_co2_kg",
        "fuente_busqueda_ref", "detalles_extra"}, ...],
        "predicciones": {...} | None}`."""


class GoogleFlightsApiClient(GoogleFlightsClient):
    """Implementación real sobre `serpapi.com/search.json`."""

    _BASE_URL = "https://serpapi.com/search.json"

    def __init__(self, api_key: str, timeout: float = 20.0) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self.llamadas_realizadas = 0

    async def buscar(self, origen: str, destino: str, fecha: str, clase: str = "economy") -> dict | None:
        params = {
            "engine": "google_flights",
            "departure_id": origen,
            "arrival_id": destino,
            "outbound_date": fecha,
            "type": "2",  # solo ida — confirmado real en el doc de hallazgos
            "currency": "USD",
            "hl": "en",
            "api_key": self._api_key,
        }
        travel_class = _CLASE_A_TRAVEL_CLASS.get(clase)
        if travel_class:
            params["travel_class"] = str(travel_class)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(self._BASE_URL, params=params)
            self.llamadas_realizadas += 1
            resp.raise_for_status()
            datos = resp.json()

        candidatos = (datos.get("best_flights") or []) + (datos.get("other_flights") or [])
        validos = [it for it in candidatos if _ruta_coincide(it, origen, destino)]

        vuelos = []
        for itinerario in validos:
            tramo = itinerario["flights"][0]
            numero = normalizar_numero_vuelo(tramo.get("flight_number") or "")
            if not numero:
                continue
            emisiones_g = (itinerario.get("carbon_emissions") or {}).get("this_flight")
            vuelos.append(
                {
                    "numero_vuelo": numero,
                    "precio": itinerario.get("price"),
                    "emisiones_co2_kg": round(emisiones_g / 1000, 2) if emisiones_g else None,
                    "fuente_busqueda_ref": itinerario.get("booking_token"),
                    "detalles_extra": {
                        "legroom": tramo.get("legroom"),
                        "extensions": tramo.get("extensions"),
                        "airplane": tramo.get("airplane"),
                    },
                }
            )

        predicciones = None
        insights = datos.get("price_insights")
        if insights:
            rango = insights.get("typical_price_range") or [None, None]
            predicciones = {
                "precio_minimo_historico": insights.get("lowest_price"),
                "nivel_precio": insights.get("price_level"),
                "rango_tipico_min": rango[0],
                "rango_tipico_max": rango[1] if len(rango) > 1 else None,
                "historico_precios": insights.get("price_history"),
            }

        if not vuelos and predicciones is None:
            return None
        return {"vuelos": vuelos, "predicciones": predicciones}
