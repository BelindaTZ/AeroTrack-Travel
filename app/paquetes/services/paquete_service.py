"""RF-PAQ-001-005 (CU-O76-O80) — construir un paquete acumulando
componentes reales de cada módulo dueño en `reserva_items`, ver el
desglose de ahorro, cambiar un componente sin perder el resto, ver
condiciones por componente y agregar traslado aeropuerto.

Paquetes no tiene catálogo propio (`paquetes-spec.md`): un paquete ES una
reserva con ≥2 `tipo_producto` distintos en `reserva_items`
(`reservas.es_paquete = true`). Este servicio reutiliza `ReservasRepository`
para toda la escritura sobre `reservas`/`reserva_items`/`reserva_extras` —
nunca duplica esa lógica.

**Alcance de esta ronda:** igual que Carrito, los componentes se agregan
por ID directo (el pasajero ya eligió su vuelo/hotel/auto/actividad en la
pantalla real de cada módulo) — no hay una pantalla de construcción de
paquete unificada todavía.
"""

import datetime
import secrets
import string

from app.paquetes.repositories.paquetes_repo import PaquetesRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client
from app.vuelos.repositories.vuelos_repo import VuelosRepository

# Orden canónico para armar el string `combinacion` de `tipos_paquete_descuento`
# — coincide con los ejemplos reales del catálogo ("vuelo+hotel",
# "vuelo+hotel+auto"): vuelo y hotel siempre primero (son los obligatorios,
# RN-PAQ-001), el resto en orden fijo para que la combinación sea determinista.
ORDEN_TIPOS = ["vuelo", "hotel", "auto", "actividad", "crucero"]
TIPOS_OBLIGATORIOS = {"vuelo", "hotel"}

_CAMPOS_ID_POR_TIPO = {
    "vuelo": ["vuelo_id", "tarifa_vuelo_id"],
    "hotel": ["hotel_id", "hotel_tarifa_id"],
    "auto": ["auto_id"],
    "actividad": ["actividad_id", "actividad_horario_id"],
    "crucero": ["crucero_id", "crucero_camarote_id"],
}


class ReservaNoEncontrada(Exception):
    pass


class SinPermiso(Exception):
    pass


class ComponenteObligatorioFaltante(Exception):
    def __init__(self, faltantes: set[str]) -> None:
        self.faltantes = faltantes
        super().__init__(f"Faltan componentes obligatorios: {', '.join(sorted(faltantes))}")


def _ahora_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


def _generar_codigo_reserva() -> str:
    alfabeto = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(6))


def _combinacion_de(tipos_presentes: set[str]) -> str:
    return "+".join(t for t in ORDEN_TIPOS if t in tipos_presentes)


async def _reserva_del_pasajero_o_error(reservas_repo: ReservasRepository, pasajero_id: str, reserva_id: str) -> dict:
    reserva = await reservas_repo.obtener_reserva(reserva_id)
    if reserva is None:
        raise ReservaNoEncontrada()
    if reserva["pasajero_titular_id"] != pasajero_id:
        raise SinPermiso()
    return reserva


async def _recalcular_totales(reservas_repo: ReservasRepository, reserva_id: str) -> dict:
    items = await reservas_repo.items_de_reserva(reserva_id)
    tipos_presentes = {item["tipo_producto"] for item in items}
    subtotal = round(sum(item.get("precio_final") or 0.0 for item in items), 2)
    return await reservas_repo.actualizar_reserva(
        reserva_id, {"es_paquete": len(tipos_presentes) >= 2, "total_pagar": subtotal}
    )


async def iniciar_paquete(pasajero_id: str, vuelo_id: str, tarifa_vuelo_id: str, precio_final: float) -> dict:
    """RF-PAQ-001 — primer componente (siempre vuelo, es obligatorio junto
    con hotel, RN-PAQ-001). Crea la reserva header y el primer `reserva_items`."""
    reservas_repo = ReservasRepository()
    ahora = _ahora_iso()

    reserva = await reservas_repo.crear_reserva(
        {
            "codigo_reserva": _generar_codigo_reserva(),
            "pasajero_titular_id": pasajero_id,
            "canal": "autoservicio",
            "estado": "pendiente_pago",
            "es_paquete": False,
            "total_pagar": precio_final,
            "fecha_reserva": ahora,
        }
    )
    await reservas_repo.crear_item(
        {
            "reserva_id": reserva["id"],
            "tipo_producto": "vuelo",
            "vuelo_id": vuelo_id,
            "tarifa_vuelo_id": tarifa_vuelo_id,
            "precio_final": precio_final,
            "estado_item": "pendiente",
        }
    )
    return reserva


async def agregar_componente(pasajero_id: str, reserva_id: str, tipo_producto: str, ids: dict, precio_final: float) -> dict:
    """RF-PAQ-001 — agrega hotel/auto/actividad al paquete en construcción."""
    reservas_repo = ReservasRepository()
    await _reserva_del_pasajero_o_error(reservas_repo, pasajero_id, reserva_id)

    data = {"reserva_id": reserva_id, "tipo_producto": tipo_producto, "precio_final": precio_final, "estado_item": "pendiente"}
    for campo in _CAMPOS_ID_POR_TIPO[tipo_producto]:
        if campo in ids:
            data[campo] = ids[campo]

    item = await reservas_repo.crear_item(data)
    await _recalcular_totales(reservas_repo, reserva_id)
    return item


async def cambiar_componente(pasajero_id: str, reserva_id: str, item_id: str, nuevos_ids: dict, precio_final: float) -> dict:
    """RF-PAQ-003 (REG-J10) — reemplaza un componente sin perder los demás."""
    reservas_repo = ReservasRepository()
    await _reserva_del_pasajero_o_error(reservas_repo, pasajero_id, reserva_id)

    data = {"precio_final": precio_final}
    data.update(nuevos_ids)
    item = await reservas_repo.actualizar_item(item_id, data)
    await _recalcular_totales(reservas_repo, reserva_id)
    return item


async def calcular_resumen(reserva_id: str) -> dict:
    """RF-PAQ-002 — desglose de ahorro: precio de cada componente por
    separado, subtotal, % de descuento según la combinación exacta, y
    precio final del paquete (REG-G2, transparencia total)."""
    reservas_repo = ReservasRepository()
    paquetes_repo = PaquetesRepository()

    items = await reservas_repo.items_de_reserva(reserva_id)
    tipos_presentes = {item["tipo_producto"] for item in items}
    subtotal = round(sum(item.get("precio_final") or 0.0 for item in items), 2)
    combinacion = _combinacion_de(tipos_presentes)

    descuento = await paquetes_repo.descuento_por_combinacion(combinacion)
    porcentaje = descuento["porcentaje_descuento"] if descuento else 0.0
    monto_descuento = round(subtotal * porcentaje / 100, 2)
    precio_final_paquete = round(subtotal - monto_descuento, 2)

    return {
        "componentes": [{"tipo_producto": i["tipo_producto"], "precio_final": i.get("precio_final")} for i in items],
        "combinacion": combinacion,
        "subtotal": subtotal,
        "porcentaje_descuento": porcentaje,
        "monto_descuento": monto_descuento,
        "precio_final_paquete": precio_final_paquete,
    }


async def confirmar_paquete(pasajero_id: str, reserva_id: str) -> dict:
    """RF-PAQ-001/RN-PAQ-001/RN-PAQ-002 — valida vuelo+hotel obligatorios,
    y COPIA el descuento vigente a la reserva (no se recalcula después,
    aunque `tipos_paquete_descuento` cambie más tarde)."""
    reservas_repo = ReservasRepository()
    await _reserva_del_pasajero_o_error(reservas_repo, pasajero_id, reserva_id)

    resumen = await calcular_resumen(reserva_id)
    tipos_presentes = {c["tipo_producto"] for c in resumen["componentes"]}
    faltantes = TIPOS_OBLIGATORIOS - tipos_presentes
    if faltantes:
        raise ComponenteObligatorioFaltante(faltantes)

    return await reservas_repo.actualizar_reserva(
        reserva_id,
        {
            "es_paquete": True,
            "descuento_paquete_pct": resumen["porcentaje_descuento"],
            "total_pagar": resumen["precio_final_paquete"],
        },
    )


async def _condicion_de_item(item: dict) -> dict:
    """RF-PAQ-004 — cada módulo dueño de su dato, este servicio solo
    agrega en una sola vista (nunca una política única simplificada)."""
    client = get_pocketbase_client()
    tipo = item["tipo_producto"]
    base = {"tipo_producto": tipo, "condiciones": None}

    try:
        if tipo == "vuelo":
            vuelos_repo = VuelosRepository()
            tarifa = await vuelos_repo.obtener_tarifa(item["tarifa_vuelo_id"])
            if tarifa:
                nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
                politica = await vuelos_repo.politica_reembolso(nivel["politica_reembolso_id"])
                base["condiciones"] = {
                    "politica_nombre": politica["nombre"],
                    "porcentaje_reembolso": politica["porcentaje_reembolso"],
                    "ventana_horas": politica["ventana_horas"],
                }
        elif tipo == "hotel":
            tarifa = await client.get_record("hoteles_tarifas", item["hotel_tarifa_id"])
            base["condiciones"] = {
                "reembolsable": tarifa.get("reembolsable"),
                "cancelacion_hasta": tarifa.get("cancelacion_hasta"),
            }
        elif tipo in ("auto", "actividad", "crucero"):
            coleccion = {
                "auto": ("autos_catalogo", item.get("auto_id")),
                "actividad": ("actividades_catalogo", item.get("actividad_id")),
                "crucero": ("cruceros_camarotes_tarifa", item.get("crucero_camarote_id")),
            }[tipo]
            nombre_coleccion, registro_id = coleccion
            if registro_id:
                registro = await client.get_record(nombre_coleccion, registro_id)
                politica_id = registro.get("politica_reembolso_id")
                if politica_id:
                    politica = await client.get_record("politicas_reembolso", politica_id)
                    base["condiciones"] = {
                        "politica_nombre": politica["nombre"],
                        "porcentaje_reembolso": politica["porcentaje_reembolso"],
                        "ventana_horas": politica["ventana_horas"],
                    }
    except (PocketBaseError, KeyError):
        base["condiciones"] = None  # dato no disponible, no se inventa

    return base


async def condiciones_por_componente(reserva_id: str) -> list[dict]:
    """RF-PAQ-004 — política de cancelación real de cada componente,
    nunca una sola política simplificada para todo el paquete."""
    reservas_repo = ReservasRepository()
    items = await reservas_repo.items_de_reserva(reserva_id)
    return [await _condicion_de_item(item) for item in items]


async def agregar_traslado_aeropuerto(pasajero_id: str, reserva_id: str, descripcion: str, precio: float) -> dict:
    """RF-PAQ-005 — mismo mecanismo que equipaje/asiento/seguro
    (`reserva_extras`), no una tabla propia."""
    reservas_repo = ReservasRepository()
    await _reserva_del_pasajero_o_error(reservas_repo, pasajero_id, reserva_id)
    return await reservas_repo.agregar_extra(reserva_id, "traslado_aeropuerto", descripcion, precio)
