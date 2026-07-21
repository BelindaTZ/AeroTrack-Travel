"""Maps Embed API — nunca la llama nuestro backend (no hay cuota que
gatear aquí): son URLs de iframe que carga el navegador del usuario
directamente contra Google. Confirmado sin cuota configurada en el
sistema (Cuotas y Límites → IAM, 2026-07-20)."""

import urllib.parse

_BASE_URL = "https://www.google.com/maps/embed/v1"


def url_mapa_punto(lat: float, lng: float, api_key: str, zoom: int = 15) -> str:
    """Modo `place` — un solo punto (ej. ubicación de un hotel)."""
    params = {"key": api_key, "q": f"{lat},{lng}", "zoom": str(zoom)}
    return f"{_BASE_URL}/place?{urllib.parse.urlencode(params)}"


def url_mapa_ruta(paradas: list[str], api_key: str) -> str | None:
    """Modo `directions` — origen/destino/escalas como TEXTO (nombres de
    puerto/ciudad), no coordenadas: evita depender de Geocoding para el
    itinerario de cruceros, que solo trae nombres de puerto. `None` si no
    hay al menos 2 paradas (directions necesita origen y destino)."""
    paradas_validas = [p for p in paradas if p]
    if len(paradas_validas) < 2:
        return None
    origen, *intermedias, destino = paradas_validas
    params = {"key": api_key, "origin": origen, "destination": destino}
    if intermedias:
        params["waypoints"] = "|".join(intermedias)
    return f"{_BASE_URL}/directions?{urllib.parse.urlencode(params)}"
