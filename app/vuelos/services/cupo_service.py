"""RF-VUE-005 (CU-O45) — verificación y decremento atómico de cupo.

Único punto de acceso a `tarifas_vuelo.cupos_disponibles` desde cualquier
módulo: Reservas invoca `verificar_y_reservar_cupo`, nunca escribe la
colección directamente — es la única forma de no romper la atomicidad
garantizada aquí (RNF-VUE-003).

Atomicidad: PocketBase no ofrece una operación atómica de decremento vía
REST (no existe un `$inc`). La garantía real es un `asyncio.Lock` por
`tarifa_id` que serializa lectura+escritura dentro de este proceso —
correcto porque `app-travel` corre como una sola instancia (ver nota de
escalabilidad en `plan.md`). Si el despliegue pasara a múltiples réplicas,
este mecanismo debe migrar a un lock distribuido o a una operación atómica
de base de datos.
"""

import asyncio
from collections import defaultdict

from app.shared.pocketbase_client import get_pocketbase_client

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


async def verificar_y_reservar_cupo(tarifa_id: str, cantidad: int = 1) -> bool:
    """Si hay cupo suficiente, lo decrementa y devuelve True. Si no, no toca
    el dato y devuelve False."""
    async with _locks[tarifa_id]:
        client = get_pocketbase_client()
        tarifa = await client.get_record("tarifas_vuelo", tarifa_id)
        disponibles = tarifa["cupos_disponibles"]
        if disponibles < cantidad:
            return False
        await client.update_record(
            "tarifas_vuelo", tarifa_id, {"cupos_disponibles": disponibles - cantidad}
        )
        return True
