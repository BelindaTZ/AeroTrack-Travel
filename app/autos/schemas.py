from pydantic import BaseModel


class AutoBusquedaOut(BaseModel):
    id: str
    modelo: str
    categoria: str
    transmision: str | None = None
    proveedor_agregador: str
    ciudad_recogida: str
    precio_dia: float
    moneda: str
    modalidad_pago_disponible: str | None = None
    dias: int | None = None
    precio_total: float | None = None
