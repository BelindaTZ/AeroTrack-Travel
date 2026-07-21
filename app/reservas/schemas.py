from pydantic import BaseModel


class ExtraOut(BaseModel):
    tipo: str
    descripcion: str | None = None
    precio: float


class ItemReservaOut(BaseModel):
    """Ítem genérico de una reserva multi-producto (creada vía Carrito,
    sin `vuelo_id`) — descripción legible resuelta contra el módulo dueño
    de cada tipo_producto (`app.shared.descripcion_producto`)."""

    tipo_producto: str
    titulo: str
    href: str | None = None
    cantidad: float = 1
    precio_final: float


class ReservaDetalleOut(BaseModel):
    id: str
    codigo_reserva: str
    estado: str
    canal: str
    total_pagar: float
    fecha_reserva: str
    fecha_expiracion_pago: str | None = None
    # Campos específicos de una reserva de un solo vuelo (flujo directo,
    # `reservas.vuelo_id` presente) — None para reservas multi-producto
    # creadas vía Carrito, ver `es_multiproducto`/`items` abajo.
    numero_vuelo: str | None = None
    aerolinea_nombre: str | None = None
    origen_legible: str | None = None
    destino_legible: str | None = None
    fecha_salida: str | None = None
    hora_salida_programada: str | None = None
    nivel_tarifa: str | None = None
    precio_tarifa: float | None = None
    extras: list[ExtraOut] = []
    # Reserva multi-producto (2026-07-19) — creada vía Carrito, sin
    # `vuelo_id`; se describe por sus `reserva_items` en vez del bloque
    # de vuelo de arriba.
    es_multiproducto: bool = False
    items: list[ItemReservaOut] = []
