"""RF-FAC-003,004 (CU-O34,O35) — comisión de la aerolínea sobre un pago
exitoso y su conciliación manual (RN-FAC-003: nunca revierte)."""

import datetime

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.vuelos.repositories.vuelos_repo import VuelosRepository


class ComisionNoEncontrada(Exception):
    pass


class ComisionYaCobrada(Exception):
    pass


async def registrar_comision(reserva: dict, vuelo: dict, pago: dict) -> dict:
    vuelos_repo = VuelosRepository()
    aerolinea = await vuelos_repo.obtener_aerolinea(vuelo["aerolinea_id"])
    monto = round(pago["monto"] * aerolinea["comision_pactada_pct"] / 100, 2)

    repo = FacturacionRepository()
    return await repo.crear_comision(
        {
            "reserva_id": reserva["id"],
            "aerolinea_id": aerolinea["id"],
            "monto": monto,
            "estado": "pendiente_cobro",
        }
    )


async def marcar_cobrada(comision_id: str) -> dict:
    """RN-FAC-003 — única transición posible es pendiente_cobro -> cobrada;
    no existe ningún endpoint ni parámetro que revierta una comisión ya
    marcada como cobrada."""
    repo = FacturacionRepository()
    comision = await repo.obtener_comision(comision_id)
    if comision is None:
        raise ComisionNoEncontrada()
    if comision["estado"] == "cobrada":
        raise ComisionYaCobrada()

    ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    return await repo.actualizar_comision(
        comision_id, {"estado": "cobrada", "fecha_cobro_real": ahora_iso}
    )
