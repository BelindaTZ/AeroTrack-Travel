from pydantic import BaseModel


class PagoOut(BaseModel):
    id: str
    reserva_id: str
    monto: float
    moneda: str
    estado: str
    fecha_pago: str | None = None
    numero_vuelo: str | None = None
    codigo_reserva: str | None = None
