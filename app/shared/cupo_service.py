"""Verificación y decremento/liberación atómica de cupo — generaliza el
patrón que ya usaba en solitario `app.vuelos.services.cupo_service`
(RF-VUE-005, CU-O45) al resto de colecciones de catálogo que exponen un
campo de cupo (`hoteles_tarifas`, `actividades_horarios`,
`cruceros_camarotes_tarifa` — real o sintético, da igual para este
servicio). Único punto de acceso: ningún módulo escribe estos campos
directo, siempre pasa por aquí.

Atomicidad: mismo mecanismo que el original — `asyncio.Lock` por
`(coleccion, registro_id)`, correcto porque `app-travel` corre como una
sola instancia (ver nota de escalabilidad heredada). Si el registro no
tiene el campo de cupo (p. ej. `autos_catalogo`, sin ese concepto), se
trata como "sin restricción" — no hay nada que verificar ni decrementar.
"""

import asyncio
from collections import defaultdict

from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client

_locks: dict[tuple[str, str], asyncio.Lock] = defaultdict(asyncio.Lock)


async def verificar_y_reservar_cupo(
    coleccion: str, registro_id: str, campo_cupo: str = "cupos_disponibles", cantidad: int = 1
) -> bool:
    """Si hay cupo suficiente (o el registro no tiene ese campo), lo
    decrementa cuando aplica y devuelve True. Si no alcanza, no toca el
    dato y devuelve False. Registro inexistente también devuelve False."""
    async with _locks[(coleccion, registro_id)]:
        client = get_pocketbase_client()
        try:
            registro = await client.get_record(coleccion, registro_id)
        except PocketBaseError:
            return False
        disponibles = registro.get(campo_cupo)
        if disponibles is None:
            return True  # la colección no modela cupo para este producto (ej. autos_catalogo)
        if disponibles < cantidad:
            return False
        await client.update_record(coleccion, registro_id, {campo_cupo: disponibles - cantidad})
        return True


async def liberar_cupo(
    coleccion: str, registro_id: str, campo_cupo: str = "cupos_disponibles", cantidad: int = 1
) -> None:
    """Inversa de `verificar_y_reservar_cupo` — libera cupo al cancelar o
    expirar una reserva. Silenciosa si el registro ya no existe o no tiene
    ese campo (nada que liberar)."""
    async with _locks[(coleccion, registro_id)]:
        client = get_pocketbase_client()
        try:
            registro = await client.get_record(coleccion, registro_id)
        except PocketBaseError:
            return
        actual = registro.get(campo_cupo)
        if actual is None:
            return
        await client.update_record(coleccion, registro_id, {campo_cupo: actual + cantidad})
