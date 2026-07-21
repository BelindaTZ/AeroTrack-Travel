from pydantic import BaseModel


class CruceroBusquedaOut(BaseModel):
    id: str
    naviera_nombre: str
    barco_nombre: str
    fecha_zarpe: str
    duracion_dias: float | None = None
    precio_base: float
    moneda: str
    puertos: list[str] = []
