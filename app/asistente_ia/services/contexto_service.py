"""REG-H1 — la pieza que hace cumplir "contexto de IA acotado y
verificable": se ejecuta ANTES de invocar al LLM, recolecta datos REALES
relevantes al mensaje del pasajero, y es lo único que el LLM puede citar
como hecho específico. Nunca inventa: si no encuentra nada verificable
para lo que el pasajero pregunta, el contexto queda vacío en ese punto —
`asistente_service` decide qué hacer con eso (nunca aproxima).

Detección de intención por palabras clave, no NLU — es deliberadamente
simple: la pieza que importa para REG-H1 no es qué tan lista es la
detección, es que TODO dato citado venga de una consulta real, nunca del
conocimiento general del LLM. Una detección más sofisticada (vía el
propio LLM) puede reemplazar esto sin tocar la garantía de fondo."""

import re

from app.reservas.repositories.reservas_repo import ReservasRepository

_PATRON_CODIGO_RESERVA = re.compile(r"\b[A-Z0-9]{4,14}\b")


async def _contexto_reserva(pasajero_id: str | None, mensaje: str) -> dict | None:
    """CU-O108 — consulta transaccional: solo si el pasajero tiene sesión
    Y la reserva mencionada le pertenece a él (RN-IA-002/REG-H1 "respeta
    los permisos del usuario que invoca") — nunca los datos de otro
    pasajero, aunque el código sea válido."""
    if not pasajero_id:
        return None
    for candidato in _PATRON_CODIGO_RESERVA.findall(mensaje.upper()):
        reserva = await ReservasRepository().obtener_por_codigo(candidato)
        if reserva and reserva.get("pasajero_titular_id") == pasajero_id:
            return {
                "tipo": "reserva_propia",
                "codigo_reserva": reserva["codigo_reserva"],
                "estado": reserva["estado"],
                "total_pagar": reserva["total_pagar"],
                "fecha_reserva": reserva["fecha_reserva"],
                "es_paquete": reserva.get("es_paquete", False),
            }
    return None


_PALABRAS_VISA = ("visa", "requisito", "pasaporte", "documento de viaje", "documentos de viaje")


async def _contexto_visa(mensaje: str) -> dict | None:
    """CU-O107 — consulta informativa de requisitos de viaje. Lee
    `requisitos_visa_cache` (propiedad de Reservas, RF-RES-008) — esa
    colección todavía no tiene ningún escritor real en este proyecto
    (RF-RES-008 sin implementar), así que esta consulta hoy siempre
    encuentra vacío. Es el comportamiento correcto, no un placeholder:
    sin dato real cacheado, no hay nada verificable que citar."""
    texto = mensaje.lower()
    if not any(p in texto for p in _PALABRAS_VISA):
        return None

    from app.shared.pocketbase_client import get_pocketbase_client
    client = get_pocketbase_client()
    resultado = await client.list_records("requisitos_visa_cache", {"perPage": 1})
    if not resultado["items"]:
        return {"tipo": "visa_sin_dato_cacheado"}
    return {"tipo": "visa", "resultado": resultado["items"][0]["resultado"]}


async def resolver_contexto(pasajero_id: str | None, mensaje: str) -> list[dict]:
    """Retorna la lista de hechos verificados relevantes al mensaje —
    puede estar vacía. `asistente_service` decide la respuesta a partir
    de ESTA lista, nunca del mensaje crudo directamente."""
    hechos = []
    reserva = await _contexto_reserva(pasajero_id, mensaje)
    if reserva:
        hechos.append(reserva)
    visa = await _contexto_visa(mensaje)
    if visa:
        hechos.append(visa)
    return hechos
