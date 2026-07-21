from pydantic import BaseModel


class ActividadBusquedaOut(BaseModel):
    id: str
    nombre: str
    ciudad: str
    categoria: str | None = None
    calificacion_promedio: float | None = None
    cantidad_resenas: float | None = None
    precio_desde: float | None = None
    moneda: str | None = None
    imagen_principal: str | None = None
