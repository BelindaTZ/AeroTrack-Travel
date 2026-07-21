"""Única puerta a Places API (New) de Google Cloud. El resto del sistema
depende de la interfaz abstracta `PlacesClient`, no del proveedor
concreto (mismo patrón que `HotelLensClient`/`TravelAdvisorClient`).

Sin UI conectada todavía en este alcance (2026-07-20) — la base queda
lista para la fase del selector estilo Despegar (Places autocomplete en
vez de la lista curada de 40 ciudades de Hoteles/Autos/Actividades).
Límite real confirmado: 100/día para autocomplete/getPlace (Cuotas y
Límites → IAM), gateado por
`app/shared/cuota_service.cupo_diario_disponible`.
"""

import abc

import httpx

from app.shared.cuota_service import cupo_diario_disponible, registrar_uso_diario

_PREFIJO_CUOTA = "google_apis.places"


class PlacesClient(abc.ABC):
    @abc.abstractmethod
    async def autocompletar(self, texto: str, session_token: str | None = None) -> list[dict]:
        """Sugerencias `{"place_id", "texto"}` mientras el usuario escribe."""

    @abc.abstractmethod
    async def detalle_lugar(self, place_id: str) -> dict | None:
        """`{"nombre", "direccion", "lat", "lng"}` o None si no se pudo
        resolver (cuota agotada o el place_id ya no existe)."""


class PlacesApiClient(PlacesClient):
    """Implementación real sobre `places.googleapis.com` (Places API New)."""

    _BASE_URL = "https://places.googleapis.com/v1"

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def autocompletar(self, texto: str, session_token: str | None = None) -> list[dict]:
        if not await cupo_diario_disponible(_PREFIJO_CUOTA):
            return []
        body: dict = {"input": texto}
        if session_token:
            body["sessionToken"] = session_token
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._BASE_URL}/places:autocomplete",
                json=body,
                headers={"X-Goog-Api-Key": self._api_key, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            datos = resp.json()
        await registrar_uso_diario(_PREFIJO_CUOTA)

        sugerencias = []
        for item in datos.get("suggestions") or []:
            prediccion = item.get("placePrediction") or {}
            texto_lugar = (prediccion.get("text") or {}).get("text")
            place_id = prediccion.get("placeId")
            if place_id and texto_lugar:
                sugerencias.append({"place_id": place_id, "texto": texto_lugar})
        return sugerencias

    async def detalle_lugar(self, place_id: str) -> dict | None:
        if not await cupo_diario_disponible(_PREFIJO_CUOTA):
            return None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._BASE_URL}/places/{place_id}",
                headers={
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": "id,displayName,formattedAddress,location",
                },
            )
            resp.raise_for_status()
            datos = resp.json()
        await registrar_uso_diario(_PREFIJO_CUOTA)

        ubicacion = datos.get("location") or {}
        return {
            "nombre": (datos.get("displayName") or {}).get("text"),
            "direccion": datos.get("formattedAddress"),
            "lat": ubicacion.get("latitude"),
            "lng": ubicacion.get("longitude"),
        }
