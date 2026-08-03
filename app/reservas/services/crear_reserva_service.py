"""RF-RES-001 (CU-O21) — crear reserva autoservicio; RN-RES-001, RNF-RES-001.
RF-RES-002 (CU-O22) — crear reserva asistida, mismo mecanismo con
`canal="asistida"` y `agente_id` obligatorio.
"""

import datetime
import secrets
import string

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.cupo_service import liberar_cupo
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.vuelos.services.asientos_service import (
    AsientoNoDisponible,
    AsientoNoValido,
    SeleccionNoPermitidaAun,
    liberar_asiento,
    validar_y_reservar_asiento,
)
from app.vuelos.services.cupo_service import verificar_y_reservar_cupo

DEFAULT_EXPIRACION_MINUTOS = 15


class PasajeroNoEncontrado(Exception):
    pass


class TarifaNoEncontrada(Exception):
    pass


class PrecioDesactualizado(Exception):
    def __init__(self, precio_actual: float):
        self.precio_actual = precio_actual
        super().__init__(f"El precio cambió a {precio_actual}")


class CupoNoDisponible(Exception):
    pass


# Re-exportadas para que routers/callers no importen directo de
# asientos_service — mismo criterio que el resto de excepciones de este
# módulo (todas las que puede lanzar crear_reserva viven acá).
__all__ = [
    "AsientoNoDisponible",
    "AsientoNoValido",
    "CupoNoDisponible",
    "PasajeroNoEncontrado",
    "PrecioDesactualizado",
    "SeleccionNoPermitidaAun",
    "TarifaNoEncontrada",
    "crear_reserva",
    "crear_reserva_asistida",
]


def _generar_codigo_reserva() -> str:
    alfabeto = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(6))


async def _minutos_expiracion(repo: ReservasRepository) -> int:
    config = await repo.config("reserva.expiracion_minutos")
    if config is None:
        return DEFAULT_EXPIRACION_MINUTOS
    try:
        return int(config["valor"])
    except (TypeError, ValueError):
        return DEFAULT_EXPIRACION_MINUTOS


async def _crear_reserva_interno(
    pasajero_id: str,
    tarifa_id: str,
    precio_esperado: float,
    canal: str,
    extras: list[dict] | None = None,
    agente_id: str | None = None,
    asiento_id: str | None = None,
) -> dict:
    repo = ReservasRepository()
    vuelos_repo = VuelosRepository()
    extras = list(extras or [])

    tarifa = await vuelos_repo.obtener_tarifa(tarifa_id)
    if tarifa is None:
        raise TarifaNoEncontrada()

    # RNF-RES-001: nunca se cobra un monto distinto al que el pasajero vio
    # — se revalida ANTES de tocar cupo, para no consumirlo si el precio
    # ya no es el que se mostró.
    if round(tarifa["precio_final"], 2) != round(precio_esperado, 2):
        raise PrecioDesactualizado(tarifa["precio_final"])

    # RN-RES-001: verificación de cupo como precondición obligatoria,
    # siempre vía el servicio de Vuelos — nunca escritura directa aquí.
    if not await verificar_y_reservar_cupo(tarifa_id):
        raise CupoNoDisponible()

    asiento = None
    if asiento_id:
        try:
            vuelo = await vuelos_repo.obtener_vuelo(tarifa["vuelo_id"])
            nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
            asiento = await validar_y_reservar_asiento(vuelo, nivel, asiento_id, repo=vuelos_repo)
        except (AsientoNoValido, AsientoNoDisponible, SeleccionNoPermitidaAun):
            # El cupo ya se reservó arriba — sin esto quedaría consumido
            # por una reserva que nunca se llega a crear (RN-RES-001).
            await liberar_cupo("tarifas_vuelo", tarifa_id, "cupos_disponibles")
            raise
        if asiento["es_premium"]:
            extras.append(
                {
                    "tipo": "asiento",
                    "descripcion": f"Asiento premium {asiento['fila']}{asiento['columna']}",
                    "precio": asiento["recargo"],
                }
            )

    total_extras = sum(e["precio"] for e in extras)
    total_pagar = round(tarifa["precio_final"] + total_extras, 2)

    ahora = datetime.datetime.now(datetime.timezone.utc)
    minutos = await _minutos_expiracion(repo)
    expiracion = ahora + datetime.timedelta(minutes=minutos)

    reserva_data = {
        "codigo_reserva": _generar_codigo_reserva(),
        "pasajero_titular_id": pasajero_id,
        "vuelo_id": tarifa["vuelo_id"],
        "tarifa_id": tarifa_id,
        "canal": canal,
        "estado": "pendiente_pago",
        "total_pagar": total_pagar,
        "fecha_reserva": ahora.strftime("%Y-%m-%d %H:%M:%S.000Z"),
        "fecha_expiracion_pago": expiracion.strftime("%Y-%m-%d %H:%M:%S.000Z"),
    }
    if agente_id:
        reserva_data["agente_id"] = agente_id

    reserva = await repo.crear_reserva(reserva_data)
    # Rediseño v3 (reserva_items): dual-write mientras el único flujo de
    # creación real es Vuelos — la cabecera sigue teniendo vuelo_id/tarifa_id
    # (compatibilidad con Facturación/Disrupciones, que los leen directo),
    # y en paralelo se registra el ítem polimórfico del que dependen
    # Paquetes/Carrito/Cuenta-Mis-Viajes.
    await repo.crear_item(
        {
            "reserva_id": reserva["id"],
            "tipo_producto": "vuelo",
            "vuelo_id": tarifa["vuelo_id"],
            "tarifa_vuelo_id": tarifa_id,
            "precio_final": tarifa["precio_final"],
            "estado_item": "pendiente",
        }
    )
    await repo.agregar_pasajero(reserva["id"], pasajero_id, asiento_id=asiento_id if asiento else None)
    for extra in extras:
        await repo.agregar_extra(
            reserva["id"], extra["tipo"], extra.get("descripcion", ""), extra["precio"]
        )

    return reserva


async def crear_reserva(
    usuario: dict,
    tarifa_id: str,
    precio_esperado: float,
    extras: list[dict] | None = None,
    asiento_id: str | None = None,
) -> dict:
    repo = ReservasRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise PasajeroNoEncontrado()
    return await _crear_reserva_interno(
        pasajero["id"],
        tarifa_id,
        precio_esperado,
        canal="autoservicio",
        extras=extras,
        asiento_id=asiento_id,
    )


async def crear_reserva_asistida(
    agente: dict,
    email_pasajero: str,
    tarifa_id: str,
    precio_esperado: float,
    extras: list[dict] | None = None,
    asiento_id: str | None = None,
) -> dict:
    repo = ReservasRepository()
    pasajero = await repo.pasajero_por_email(email_pasajero)
    if pasajero is None:
        raise PasajeroNoEncontrado()
    return await _crear_reserva_interno(
        pasajero["id"],
        tarifa_id,
        precio_esperado,
        canal="asistida",
        extras=extras,
        agente_id=agente["id"],
        asiento_id=asiento_id,
    )
