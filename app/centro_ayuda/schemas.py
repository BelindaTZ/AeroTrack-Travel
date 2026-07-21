from pydantic import BaseModel


class ArticuloBusquedaOut(BaseModel):
    id: str
    titulo: str
    categoria: str
    fecha_publicacion: str


class ArticuloDetalleOut(BaseModel):
    id: str
    titulo: str
    categoria: str
    contenido: str
    fecha_publicacion: str
    calificaciones_arriba: int
    calificaciones_abajo: int


class CasoEscaladoOut(BaseModel):
    id: str
    asunto: str
    mensaje: str
    estado: str
    gmail_thread_id: str | None = None
    fecha_creacion: str
    fecha_resolucion: str | None = None
    pasajero_nombre: str | None = None
