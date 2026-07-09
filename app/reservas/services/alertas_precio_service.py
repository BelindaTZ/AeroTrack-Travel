"""RF-RES-006 (CU-O26) — crear alerta de precio, sin reserva existente."""

from datetime import date

from app.reservas.repositories.reservas_repo import ReservasRepository


class PasajeroNoEncontrado(Exception):
    pass


async def crear_alerta(
    usuario: dict, origen: str, destino: str, fecha_objetivo: date, precio_umbral: float
) -> dict:
    repo = ReservasRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise PasajeroNoEncontrado()

    return await repo.crear_alerta(
        {
            "pasajero_id": pasajero["id"],
            "origen_codigo": origen.upper(),
            "destino_codigo": destino.upper(),
            "fecha_objetivo": fecha_objetivo.isoformat(),
            "precio_umbral": precio_umbral,
            "activa": True,
        }
    )
