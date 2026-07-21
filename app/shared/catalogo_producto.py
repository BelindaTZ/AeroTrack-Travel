"""Mapeo canónico `tipo_producto` -> colección/campos de catálogo real.

Punto único de verdad compartido por Carrito (precio vigente al
revalidar, reserva de cupo al confirmar checkout — `app/carrito/
repositories/carrito_repo.py`) y Reservas (liberación de cupo al cancelar
o expirar — `app/reservas/services/cancelar_reserva_service.py`,
`expiracion_service.py`). Antes de esto cada lado tenía su propio mapeo
parcial (o ninguno), lo que dejaba huecos: Carrito nunca validaba cupo,
y la liberación al cancelar/expirar solo existía (a medias) para vuelos.
"""

# tipo_producto -> (coleccion de catálogo, campo de precio vigente, campo
# de relación al ítem específico dentro de carrito_items/reserva_items,
# campo de cupo o None si ese tipo de producto no modela cupo — p. ej.
# autos_catalogo, una oferta = un vehículo, sin campo de inventario)
CATALOGO_POR_TIPO = {
    "vuelo": ("tarifas_vuelo", "precio_final", "tarifa_vuelo_id", "cupos_disponibles"),
    "hotel": ("hoteles_tarifas", "precio_final", "hotel_tarifa_id", "cupos_disponibles"),
    "auto": ("autos_catalogo", "precio_dia", "auto_id", None),
    "actividad": ("actividades_horarios", "precio", "actividad_horario_id", "cupos_disponibles"),
    "crucero": ("cruceros_camarotes_tarifa", "precio_por_persona", "crucero_camarote_id", "cupos_disponibles"),
}
