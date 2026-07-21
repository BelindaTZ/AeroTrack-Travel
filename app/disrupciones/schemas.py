from pydantic import BaseModel


class DisrupcionOut(BaseModel):
    id: str
    vuelo_id: str
    fuente_deteccion: str
    tipo_cambio: str
    estado: str
    detalle: str | None = None


class NotificacionOut(BaseModel):
    id: str
    pasajero_id: str
    reserva_id: str
    disrupcion_id: str | None = None
    canal: str
    asunto: str
    estado_envio: str
    leida: bool
    fecha_envio: str | None = None
