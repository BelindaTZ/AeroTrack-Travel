"""RF-VUE-005 (CU-O45) — verificación y decremento atómico de cupo de
`tarifas_vuelo`. Delega en `app.shared.cupo_service` (generalizado
2026-07-19 para que Hoteles/Actividades/Cruceros compartan el mismo
mecanismo de lock+decremento vía Carrito) — esta función conserva su
firma pública exacta porque `crear_reserva_service.py`/
`modificar_reserva_service.py`/`pago_stub_service.py` ya la invocan así.
"""

from app.shared.cupo_service import verificar_y_reservar_cupo as _verificar_y_reservar_cupo_generico


async def verificar_y_reservar_cupo(tarifa_id: str, cantidad: int = 1) -> bool:
    """Si hay cupo suficiente, lo decrementa y devuelve True. Si no, no toca
    el dato y devuelve False."""
    return await _verificar_y_reservar_cupo_generico("tarifas_vuelo", tarifa_id, "cupos_disponibles", cantidad)
