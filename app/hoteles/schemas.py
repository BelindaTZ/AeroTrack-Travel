from pydantic import BaseModel


class HotelBusquedaOut(BaseModel):
    id: str
    nombre: str
    ciudad: str
    estrellas: float | None = None
    calificacion_promedio: float | None = None
    cantidad_resenas: float | None = None
    precio_desde: float | None = None
    moneda: str = "USD"
    imagen_principal: str | None = None
