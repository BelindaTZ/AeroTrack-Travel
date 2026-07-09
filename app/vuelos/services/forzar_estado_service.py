"""RF-VUE-006 (CU-O48) — ajuste puntual excepcional, solo para demo.

Vía EXCEPCIONAL fuera del flujo de negocio normal (ver `vuelos-spec.md`,
Funcionalidad 5). Reutiliza `estado_service.actualizar_estado(origen="manual")`
para heredar el marcado RN-VUE-005 (queda distinguible de un cambio real)
sin duplicar esa lógica aquí.
"""

from app.vuelos.services.estado_service import actualizar_estado

ESTADOS_DISRUPCION = {"retrasado", "cancelado", "desviado"}


class MotivoRequerido(Exception):
    pass


async def forzar_estado(vuelo_id: str, nuevo_estado: str, motivo: str) -> dict:
    # RN-VUE-006: sin motivo explícito, el ajuste se rechaza antes de tocar
    # cualquier dato — ninguna otra validación corre primero.
    if not motivo or not motivo.strip():
        raise MotivoRequerido()
    return await actualizar_estado(vuelo_id, nuevo_estado, origen="manual")


def es_disrupcion(estado: str) -> bool:
    return estado in ESTADOS_DISRUPCION
