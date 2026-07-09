"""RF-VUE-004 (CU-O20) — punto de escritura genérico de `vuelos_catalogo.estado`.

Consumido por CU-O48 (Fase 5, este módulo) y, cuando exista, por
`disrupciones-spec.md` al detectar un cambio real. La transición
automática por horario vencido (`programado` → `completado`) sigue
viviendo en `dags/catalogo_vuelos_tasks.py` (ya en producción) — este
servicio es el punto de escritura para cualquier OTRO caller que necesite
fijar un estado explícito.
"""

import datetime

from app.shared.pocketbase_client import get_pocketbase_client

ESTADOS_VALIDOS = {"programado", "retrasado", "cancelado", "completado", "desviado"}


class EstadoInvalido(Exception):
    pass


async def actualizar_estado(vuelo_id: str, nuevo_estado: str, origen: str = "automatico") -> dict:
    if nuevo_estado not in ESTADOS_VALIDOS:
        raise EstadoInvalido(f"'{nuevo_estado}' no es un estado válido: {sorted(ESTADOS_VALIDOS)}")

    client = get_pocketbase_client()
    ahora = datetime.datetime.now(datetime.timezone.utc)
    campos = {
        "estado": nuevo_estado,
        "fecha_actualizacion_estado": ahora.strftime("%Y-%m-%d %H:%M:%S.000Z"),
    }
    # RN-VUE-005: un ajuste manual (CU-O48) se marca `generado_por="manual"`
    # para quedar siempre distinguible de un cambio real; un cambio con
    # origen "automatico" (Disrupciones, el DAG) nunca toca este campo.
    if origen == "manual":
        campos["generado_por"] = "manual"

    return await client.update_record("vuelos_catalogo", vuelo_id, campos)
