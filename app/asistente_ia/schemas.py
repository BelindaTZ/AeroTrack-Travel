from pydantic import BaseModel


class MensajeOut(BaseModel):
    id: str
    rol: str
    contenido: str
    calificacion: str | None = None
    fecha: str


class ConversacionOut(BaseModel):
    id: str
    titulo: str | None = None
    fecha_inicio: str
    fecha_ultima_actividad: str
    activa: bool
    mensajes: list[MensajeOut]
