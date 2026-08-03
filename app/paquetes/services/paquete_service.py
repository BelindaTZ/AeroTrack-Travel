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

**2026-07-27 — cupo/expiración conectados (antes faltaban por completo)**:
`iniciar_paquete`/`agregar_componente`/`cambiar_componente` no verificaban
ni reservaban cupo real (a diferencia de Carrito/Reservas, que siempre
pasan por `cupo_service`) — un paquete podía armarse y confirmarse sobre
un vuelo/hotel/actividad ya agotado, sin decrementar nada. Tampoco se fijaba
`fecha_expiracion_pago`, así que un paquete abandonado a medio construir
nunca expiraba ni liberaba el cupo que sí llegó a reservar. Ambos, corregidos
acá con el mismo `app.shared.cupo_service`/`CATALOGO_POR_TIPO` que ya usan
Carrito y Reservas — `auto` sigue sin concepto de cupo (`campo_cupo is None`),
y `crucero` sigue fuera de Paquetes (ningún `tipos_paquete_descuento` lo
incluye y el router de construcción no expone sus campos de id).
"""

import datetime
import secrets
import string

from app.paquetes.repositories.paquetes_repo import PaquetesRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.catalogo_producto import CATALOGO_POR_TIPO
from app.shared.cupo_service import liberar_cupo, verificar_y_reservar_cupo
from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client
from app.vuelos.repositories.vuelos_repo import VuelosRepository

# Orden canónico para armar el string `combinacion` de `tipos_paquete_descuento`
# — coincide con los ejemplos reales del catálogo ("vuelo+hotel",
# "vuelo+hotel+auto"): vuelo y hotel siempre primero (son los obligatorios,
# RN-PAQ-001), el resto en orden fijo para que la combinación sea determinista.
ORDEN_TIPOS = ["vuelo", "hotel", "auto", "actividad", "crucero"]
TIPOS_OBLIGATORIOS = {"vuelo", "hotel"}
DEFAULT_EXPIRACION_MINUTOS = 15

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


class CupoNoDisponible(Exception):
    pass


def _generar_codigo_reserva() -> str:
    alfabeto = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(6))


def combinacion_de(tipos_presentes: set[str]) -> str:
    return "+".join(t for t in ORDEN_TIPOS if t in tipos_presentes)


async def _minutos_expiracion(reservas_repo: ReservasRepository) -> int:
    config = await reservas_repo.config("reserva.expiracion_minutos")
    if config is None:
        return DEFAULT_EXPIRACION_MINUTOS
    try:
        return int(config["valor"])
    except (TypeError, ValueError):
        return DEFAULT_EXPIRACION_MINUTOS


async def verificar_propiedad(reservas_repo: ReservasRepository, pasajero_id: str, reserva_id: str) -> dict:
    """Pública (antes `_reserva_del_pasajero_o_error`) — también la usa
    `router_resumen.py` para no exponer el resumen/condiciones de un
    paquete ajeno con solo adivinar el `reserva_id` (el endpoint verificaba
    que el usuario FUERA pasajero, pero nunca que esa reserva fuera suya)."""
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

    coleccion, _, _, campo_cupo = CATALOGO_POR_TIPO["vuelo"]
    if not await verificar_y_reservar_cupo(coleccion, tarifa_vuelo_id, campo_cupo):
        raise CupoNoDisponible()

    ahora = datetime.datetime.now(datetime.timezone.utc)
    minutos = await _minutos_expiracion(reservas_repo)
    expiracion = ahora + datetime.timedelta(minutes=minutos)

    reserva = await reservas_repo.crear_reserva(
        {
            "codigo_reserva": _generar_codigo_reserva(),
            "pasajero_titular_id": pasajero_id,
            "canal": "autoservicio",
            "estado": "pendiente_pago",
            "es_paquete": False,
            "total_pagar": precio_final,
            "fecha_reserva": ahora.strftime("%Y-%m-%d %H:%M:%S.000Z"),
            "fecha_expiracion_pago": expiracion.strftime("%Y-%m-%d %H:%M:%S.000Z"),
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
    await verificar_propiedad(reservas_repo, pasajero_id, reserva_id)

    info = CATALOGO_POR_TIPO.get(tipo_producto)
    if info is not None:
        coleccion, _, campo_id, campo_cupo = info
        registro_id = ids.get(campo_id)
        if campo_cupo is not None and registro_id:
            if not await verificar_y_reservar_cupo(coleccion, registro_id, campo_cupo):
                raise CupoNoDisponible()

    data = {"reserva_id": reserva_id, "tipo_producto": tipo_producto, "precio_final": precio_final, "estado_item": "pendiente"}
    for campo in _CAMPOS_ID_POR_TIPO[tipo_producto]:
        if campo in ids:
            data[campo] = ids[campo]

    item = await reservas_repo.crear_item(data)
    await _recalcular_totales(reservas_repo, reserva_id)
    return item


async def cambiar_componente(pasajero_id: str, reserva_id: str, item_id: str, nuevos_ids: dict, precio_final: float) -> dict:
    """RF-PAQ-003 (REG-J10) — reemplaza un componente sin perder los demás.
    Reserva el cupo del ítem nuevo ANTES de liberar el del viejo (mismo
    orden que `modificar_reserva_service.py`) — si el nuevo no tiene cupo,
    el viejo se queda intacto en vez de perder ambos."""
    reservas_repo = ReservasRepository()
    await verificar_propiedad(reservas_repo, pasajero_id, reserva_id)

    items = await reservas_repo.items_de_reserva(reserva_id)
    item_actual = next((i for i in items if i["id"] == item_id), None)
    if item_actual is None:
        raise ReservaNoEncontrada()

    info = CATALOGO_POR_TIPO.get(item_actual["tipo_producto"])
    if info is not None:
        coleccion, _, campo_id, campo_cupo = info
        registro_id_nuevo = nuevos_ids.get(campo_id)
        registro_id_actual = item_actual.get(campo_id)
        if campo_cupo is not None and registro_id_nuevo and registro_id_nuevo != registro_id_actual:
            if not await verificar_y_reservar_cupo(coleccion, registro_id_nuevo, campo_cupo):
                raise CupoNoDisponible()
            if registro_id_actual:
                await liberar_cupo(coleccion, registro_id_actual, campo_cupo)

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
    combinacion = combinacion_de(tipos_presentes)

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
    await verificar_propiedad(reservas_repo, pasajero_id, reserva_id)

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
    await verificar_propiedad(reservas_repo, pasajero_id, reserva_id)
    return await reservas_repo.agregar_extra(reserva_id, "traslado_aeropuerto", descripcion, precio)
