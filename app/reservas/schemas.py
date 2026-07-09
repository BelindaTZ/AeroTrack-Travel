from pydantic import BaseModel


class ExtraOut(BaseModel):
    tipo: str
    descripcion: str | None = None
    precio: float


class ReservaDetalleOut(BaseModel):
    id: str
    codigo_reserva: str
    estado: str
    canal: str
    total_pagar: float
    fecha_reserva: str
    fecha_expiracion_pago: str | None = None
    numero_vuelo: str
    aerolinea_nombre: str
    origen_legible: str
    destino_legible: str
    fecha_salida: str
    hora_salida_programada: str
    nivel_tarifa: str
    precio_tarifa: float
    extras: list[ExtraOut] = []
