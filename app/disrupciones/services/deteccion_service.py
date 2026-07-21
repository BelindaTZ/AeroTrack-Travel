"""RF-DIS-003 (CU-O29) — parsear un correo monitoreado para detectar si
corresponde a un cambio real de itinerario. RN-DIS-001: un correo sin vuelo
reconocido en `vuelos_catalogo` se descarta (retorna `None`), no se inventa
una disrupción sobre un vuelo que no existe.
"""

import re

from app.vuelos.repositories.vuelos_repo import VuelosRepository

_NUMERO_VUELO_RE = re.compile(r"\b([A-Z]{2}\d{2,4})\b")

# Orden de chequeo = severidad — si un correo menciona varias palabras clave
# a la vez, se queda con la primera que matchea (más severa primero).
_PALABRAS_CLAVE_POR_TIPO = [
    ("cancelacion", ["cancelled", "cancellation", "cancelado", "cancelación"]),
    ("desvio", ["diverted", "diversion", "desviado", "desvío"]),
    ("retraso", ["delayed", "delay", "retrasado", "retraso"]),
    ("cambio_puerta", ["gate change", "new gate", "cambio de puerta", "nueva puerta"]),
    ("cambio_horario", ["schedule change", "rescheduled", "new departure time", "cambio de horario"]),
]


def _detectar_tipo_cambio(texto: str) -> str | None:
    texto_lower = texto.lower()
    for tipo_cambio, palabras in _PALABRAS_CLAVE_POR_TIPO:
        if any(palabra in texto_lower for palabra in palabras):
            return tipo_cambio
    return None


async def parsear_correo_a_disrupcion(correo: dict) -> dict | None:
    texto = f"{correo.get('asunto', '')}\n{correo.get('cuerpo_texto', '')}"

    tipo_cambio = _detectar_tipo_cambio(texto)
    if tipo_cambio is None:
        return None

    match = _NUMERO_VUELO_RE.search(texto.upper())
    if match is None:
        return None
    numero_vuelo = match.group(1)

    vuelos_repo = VuelosRepository()
    vuelo = await vuelos_repo.obtener_por_numero_vuelo(numero_vuelo)
    if vuelo is None:
        # RN-DIS-001 (QP-07): vuelo no reconocido -> se descarta sin notificar.
        return None

    return {
        "vuelo_id": vuelo["id"],
        "tipo_cambio": tipo_cambio,
        "detalle": f"Detectado por correo: \"{correo.get('asunto', '')}\"",
    }
