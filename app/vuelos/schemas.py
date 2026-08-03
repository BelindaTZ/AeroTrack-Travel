from pydantic import BaseModel


class VueloBusquedaOut(BaseModel):
    id: str
    numero_vuelo: str
    aerolinea_nombre: str
    origen_codigo: str
    destino_codigo: str
    origen_legible: str
    destino_legible: str
    fecha_salida: str
    hora_salida_programada: str
    hora_llegada_programada: str
    duracion_min: int | None = None
    precio_desde: float
    equipaje_incluido: bool = False  # RF-VUE-007 — true si ALGUNA tarifa del vuelo incluye equipaje facturado


class NivelTarifaOut(BaseModel):
    id: str
    nombre: str
    descripcion: str | None = None
    equipaje_incluido: bool
    cambios_permitidos: bool
    precio_final: float
    cupos_disponibles: int
    politica_nombre: str
    politica_condiciones: str
    politica_porcentaje_reembolso: float
    politica_ventana_horas: int
    clase_cabina: str = "economy"  # RF-VUE-010 (CU-O114) — economy/business/first
