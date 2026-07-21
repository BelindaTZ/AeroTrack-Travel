from pydantic import BaseModel, Field


class ReservaHistorialOut(BaseModel):
    id: str
    codigo_reserva: str
    estado: str
    numero_vuelo: str
    aerolinea_nombre: str
    origen_legible: str
    destino_legible: str
    fecha_salida: str
    total_pagar: float
    nivel_tarifa: str


class ContactoIn(BaseModel):
    telefono: str = Field(..., min_length=7, max_length=15)
    direccion: str | None = None
    contacto_emergencia: str | None = None


class PasajeroBackofficeOut(BaseModel):
    id: str
    usuario_id: str
    nombre_completo: str
    email: str
    telefono: str | None
    direccion: str | None
    contacto_emergencia: str | None
    fecha_nacimiento: str | None


class PasajeroDetalleOut(PasajeroBackofficeOut):
    historial_reservas: list[ReservaHistorialOut]