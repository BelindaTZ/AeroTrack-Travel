"""Única puerta a Routes API (ComputeRoutes) de Google Cloud.

Sin UI conectada todavía en este alcance — candidata para mostrar
"distancia al centro" en tarjetas de hotel (patrón visto en el análisis de
Despegar de esta sesión), pendiente de diseño de producto. Límite real
confirmado: 100/día para ComputeRoutes (Cuotas y Límites → IAM,
2026-07-20), gateado por
`app/shared/cuota_service.cupo_diario_disponible`.
"""

import abc

import httpx

from app.shared.cuota_service import cupo_diario_disponible, registrar_uso_diario

_PREFIJO_CUOTA = "google_apis.routes"


class RoutesClient(abc.ABC):
    @abc.abstractmethod
    async def calcular_ruta(self, origen: str, destino: str) -> dict | None:
        """`{"distancia_metros", "duracion_segundos"}` o None si no hay
        cupo o Google no pudo calcular la ruta."""


class RoutesApiClient(RoutesClient):
    """Implementación real sobre `routes.googleapis.com` (ComputeRoutes)."""

    _BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def calcular_ruta(self, origen: str, destino: str) -> dict | None:
        if not await cupo_diario_disponible(_PREFIJO_CUOTA):
            return None
        body = {"origin": {"address": origen}, "destination": {"address": destino}, "travelMode": "DRIVE"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                self._BASE_URL,
                json=body,
                headers={
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            datos = resp.json()
        await registrar_uso_diario(_PREFIJO_CUOTA)

        rutas = datos.get("routes") or []
        if not rutas:
            return None
        ruta = rutas[0]
        duracion_str = ruta.get("duration") or "0s"
        duracion_segundos = int(duracion_str.rstrip("s")) if duracion_str.endswith("s") else None
        return {"distancia_metros": ruta.get("distanceMeters"), "duracion_segundos": duracion_segundos}
