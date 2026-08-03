"""Única puerta a AeroDataBox FIDS (Flight Information Display System) de
RapidAPI (REG-F1). El resto del sistema depende de la interfaz abstracta
`AeroDataBoxClient`, no del proveedor concreto — mismo patrón que
`HotelLensClient`/`TravelAdvisorClient`.

Flujo real confirmado (docs/apis-reference.md sección 2): `GET
/flights/airports/Iata/{code}/{fromLocal}/{toLocal}` — ventana máxima real
de 12 horas por llamada (un rango de 24h da 400 "must not be more than 12
hours"), dos llamadas cubren un día completo por aeropuerto. Un solo call a
ATL devolvió 781 salidas reales, 141 de ellas hacia otros 14 de los 15 hubs
curados — el costo es por aeropuerto de origen, no por ruta. Costo real
≈2 unidades API/llamada (plan Basic, 600/mes).

⚠️ La forma exacta de cada item de `departures[]` (bloque `movement.*`) es
la publicada por AeroDataBox — en esta sesión solo se confirmó en vivo
`number`/`aircraft.model`/`airline.iata` (apis-reference.md:59), no la
ruta completa de `movement.airport.iata`/`movement.scheduledTime.*`. Se usa
acceso defensivo (`.get()` en cascada) para no romper si algún campo
anidado no calza exacto — revisar contra la respuesta real al conectar de
verdad, antes de confiar ciegamente en este parseo.
"""

import abc
import re

import httpx

_ESPACIO_NUMERO_VUELO = re.compile(r"\s+")


def normalizar_numero_vuelo(numero: str) -> str:
    """AeroDataBox da `"DL 466"` (con espacio) — el resto del sistema
    espera `"DL466"` (confirmado real, apis-reference.md:59)."""
    return _ESPACIO_NUMERO_VUELO.sub("", numero or "")


class AeroDataBoxClient(abc.ABC):
    @abc.abstractmethod
    async def salidas(self, codigo_aeropuerto: str, desde_local: str, hasta_local: str) -> list[dict]:
        """FIDS de salidas reales en la ventana `desde_local`/`hasta_local`
        (máx. 12h reales). Cada item ya normalizado:
        `{"numero_vuelo", "destino_codigo", "avion_modelo",
        "hora_salida_local"}` — `hora_salida_local` es `"HH:MM"` o `None`
        si el item no trae hora utilizable."""


class AeroDataBoxApiClient(AeroDataBoxClient):
    """Implementación real sobre `aerodatabox.p.rapidapi.com`."""

    _BASE_URL = "https://aerodatabox.p.rapidapi.com"

    def __init__(self, api_key: str, api_host: str, timeout: float = 15.0) -> None:
        self._api_key = api_key
        self._api_host = api_host
        self._timeout = timeout
        self.llamadas_realizadas = 0

    def _headers(self) -> dict:
        return {"x-rapidapi-key": self._api_key, "x-rapidapi-host": self._api_host}

    async def salidas(self, codigo_aeropuerto: str, desde_local: str, hasta_local: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._BASE_URL}/flights/airports/Iata/{codigo_aeropuerto}/{desde_local}/{hasta_local}",
                headers=self._headers(),
            )
            self.llamadas_realizadas += 1
            resp.raise_for_status()
            datos = resp.json()

        salidas = []
        for item in datos.get("departures") or []:
            movimiento = item.get("movement") or {}
            destino_codigo = (movimiento.get("airport") or {}).get("iata")
            numero_vuelo = normalizar_numero_vuelo(item.get("number") or "")
            if not destino_codigo or not numero_vuelo:
                continue
            hora_local = (movimiento.get("scheduledTime") or {}).get("local")
            salidas.append(
                {
                    "numero_vuelo": numero_vuelo,
                    "destino_codigo": destino_codigo,
                    "avion_modelo": (item.get("aircraft") or {}).get("model") or "",
                    "hora_salida_local": hora_local[11:16] if hora_local and len(hora_local) >= 16 else None,
                }
            )
        return salidas
