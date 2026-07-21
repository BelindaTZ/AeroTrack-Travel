from pydantic import BaseModel


class OfertaOut(BaseModel):
    id: str
    tipo_producto: str
    titulo: str
    descripcion: str | None = None
    titulo_producto: str
    href_producto: str | None = None
    fecha_fin: str


class DestinoPopularOut(BaseModel):
    codigo: str
    legible: str
    volumen: int


class CuponAplicadoOut(BaseModel):
    monto_descontado: float
    nuevo_total: float
