from pydantic import BaseModel


class FavoritoOut(BaseModel):
    id: str
    tipo: str
    producto_ref: str
    fecha_guardado: str


class ViajePersonalizadoOut(BaseModel):
    id: str
    nombre: str
    descripcion: str | None = None


class BusquedaRecienteOut(BaseModel):
    id: str
    tipo_producto: str
    criterios: dict
    fecha: str
    href_relanzar: str


class MovimientoPuntosOut(BaseModel):
    tipo: str
    puntos: float
    fecha: str
    descripcion: str | None = None
    reserva_id: str | None = None
    vigente: bool


class PuntosResumenOut(BaseModel):
    saldo_vigente: float
    nivel_actual: str | None
    movimientos: list[MovimientoPuntosOut]
