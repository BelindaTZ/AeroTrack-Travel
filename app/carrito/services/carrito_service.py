"""RF-CAR-001,002,003,004 (CU-O93-O96) — ver/agregar/eliminar ítems del
carrito y checkout con revalidación de precio + conversión 1:1 a
`reserva_items` (Reservas). Reutiliza `ReservasRepository` para crear la
reserva real al confirmar — este módulo nunca duplica esa lógica.

RN-CAR-001: el precio del carrito es un snapshot; el checkout siempre
revalida contra el catálogo vigente antes de cobrar (REG-G2).
RN-CAR-002: un pasajero tiene a lo sumo un carrito `activo`.
RN-CAR-003: no se puede iniciar checkout de un carrito vacío.

**Cupo real (2026-07-19)**: mismo criterio que `carrito-spec.md` ("un
carrito no bloquea cupo") — agregar/quitar ítems del carrito NUNCA toca
inventario. El cupo se verifica y se reserva atómicamente recién al
confirmar el checkout (`app.shared.cupo_service`, generaliza RF-VUE-005),
todo o nada: si algún ítem ya no tiene cupo suficiente, no se crea ninguna
reserva y se libera lo que ya se hubiera reservado en el mismo intento.
`precio_snapshot`/`precio_final` representan siempre el precio UNITARIO;
`cantidad` (participantes de una actividad, etc.) es el multiplicador —
mantenerlos separados es lo que permite revalidar precio sin falsos
positivos cuando `cantidad > 1` (ver `errores-conocidos.md`).
"""

import datetime
import secrets
import string

from app.carrito.repositories.carrito_repo import CarritoRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.rango_fechas import fechas_rango

TIPOS_VALIDOS = {"vuelo", "hotel", "auto", "actividad", "crucero"}
DEFAULT_EXPIRACION_MINUTOS = 15

# Hotel (noches) y Auto (días) son los únicos tipos cuya `cantidad` se
# DERIVA de un rango de fechas — antes de esto, check-in/check-out y
# recogida/devolución eran cosméticos (ver errores-conocidos.md, gap
# cerrado 2026-07-29): `unidades` (habitaciones/vehículos) × noches/días.
TIPOS_CON_RANGO_FECHAS = {"hotel", "auto"}

# tipo_producto -> campos de id que se copian tal cual de carrito_items a
# reserva_items (mapeo 1:1 a propósito, mismo patrón polimórfico).
_CAMPOS_ID_POR_TIPO = {
    "vuelo": ["vuelo_id", "tarifa_vuelo_id"],
    "hotel": ["hotel_id", "hotel_tarifa_id"],
    "auto": ["auto_id"],
    "actividad": ["actividad_id", "actividad_horario_id"],
    "crucero": ["crucero_id", "crucero_camarote_id"],
}


class TipoProductoInvalido(Exception):
    pass


class ItemNoEncontrado(Exception):
    pass


class SinPermiso(Exception):
    pass


class CarritoVacio(Exception):
    pass


class RangoFechasInvalido(Exception):
    pass


class CupoInsuficiente(Exception):
    """Al menos un ítem del carrito ya no tiene cupo suficiente al
    momento de confirmar — ningún cupo reservado en este intento queda
    comprometido (se libera todo antes de propagar la excepción)."""

    def __init__(self, item_ids: list[str]):
        self.item_ids = item_ids
        super().__init__(f"Cupo insuficiente para los ítems: {item_ids}")


def _ahora_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


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


async def obtener_o_crear_carrito_activo(pasajero_id: str) -> dict:
    """RN-CAR-002 — nunca crea un segundo carrito activo en paralelo."""
    repo = CarritoRepository()
    carrito = await repo.carrito_de_trabajo(pasajero_id)
    if carrito is not None:
        return carrito
    ahora = _ahora_iso()
    return await repo.crear_carrito(
        {"pasajero_id": pasajero_id, "estado": "activo", "fecha_creacion": ahora, "fecha_ultima_actividad": ahora}
    )


async def agregar_item(
    pasajero_id: str, tipo_producto: str, ids: dict, precio_snapshot: float, cantidad: int = 1,
    modalidad_pago: str | None = None,
    fecha_inicio: str | None = None, fecha_fin: str | None = None, unidades: int = 1,
) -> dict:
    if tipo_producto not in TIPOS_VALIDOS:
        raise TipoProductoInvalido(tipo_producto)

    repo = CarritoRepository()
    carrito = await obtener_o_crear_carrito_activo(pasajero_id)
    ahora = _ahora_iso()

    data = {
        "carrito_id": carrito["id"], "tipo_producto": tipo_producto,
        "precio_snapshot": precio_snapshot, "cantidad": cantidad, "fecha_agregado": ahora,
    }
    if modalidad_pago:
        data["modalidad_pago"] = modalidad_pago

    if tipo_producto in TIPOS_CON_RANGO_FECHAS and fecha_inicio and fecha_fin:
        # `cantidad` se SOBREESCRIBE acá — nunca se confía en la del form
        # para hotel/auto, para no poder desincronizarla del rango real
        # (evita doble conteo o sub-reserva al confirmar el checkout, ver
        # `cupo_rango_service.py`). `unidades` × noches/días es el único
        # cálculo válido de cuánto cobrar; `unidades` por sí solo es lo que
        # se reserva contra CADA noche/día individual.
        noches_o_dias = len(fechas_rango(fecha_inicio, fecha_fin))
        if noches_o_dias <= 0:
            raise RangoFechasInvalido(f"fecha_fin debe ser posterior a fecha_inicio: {fecha_inicio}..{fecha_fin}")
        data["cantidad"] = unidades * noches_o_dias
        data["fecha_inicio"] = fecha_inicio
        data["fecha_fin"] = fecha_fin
        data["unidades"] = unidades

    for campo in _CAMPOS_ID_POR_TIPO[tipo_producto]:
        if campo in ids:
            data[campo] = ids[campo]

    item = await repo.crear_item(data)
    await repo.actualizar_carrito(carrito["id"], {"fecha_ultima_actividad": ahora})
    return item


async def eliminar_item(pasajero_id: str, item_id: str) -> None:
    repo = CarritoRepository()
    item = await repo.obtener_item(item_id)
    if item is None:
        raise ItemNoEncontrado()

    # Ownership real: se resuelve el carrito DUEÑO del ítem, no el carrito
    # (si acaso) del que llama — así "eliminar el ítem de otro pasajero" da
    # siempre SinPermiso, nunca CarritoVacio cuando el que llama no tiene
    # carrito propio.
    carrito = await repo.obtener_carrito(item["carrito_id"])
    if carrito is None or carrito["pasajero_id"] != pasajero_id:
        raise SinPermiso()

    await repo.eliminar_item(item_id)
    await repo.actualizar_carrito(carrito["id"], {"fecha_ultima_actividad": _ahora_iso()})


async def ver_carrito(pasajero_id: str) -> dict:
    repo = CarritoRepository()
    carrito = await repo.carrito_de_trabajo(pasajero_id)
    if carrito is None:
        return {"carrito": None, "items": [], "total": 0.0}

    items = await repo.items_de_carrito(carrito["id"])
    total = round(sum((item.get("precio_snapshot") or 0.0) * (item.get("cantidad") or 1) for item in items), 2)
    return {"carrito": carrito, "items": items, "total": total}


async def revalidar_precios(pasajero_id: str) -> dict:
    """RN-CAR-001 — compara el TOTAL de cada ítem (precio unitario ×
    cantidad) contra el catálogo vigente; no modifica nada, solo informa
    (REG-G2 exige avisar antes de cobrar, no cobrar silenciosamente un
    precio distinto)."""
    repo = CarritoRepository()
    carrito = await repo.carrito_de_trabajo(pasajero_id)
    if carrito is None:
        return {"items": [], "cambios": []}

    items = await repo.items_de_carrito(carrito["id"])
    cambios = []
    for item in items:
        cantidad = item.get("cantidad") or 1
        unitario_vigente = await repo.precio_vigente(item["tipo_producto"], item)
        snapshot = item.get("precio_snapshot")
        if unitario_vigente is None or snapshot is None:
            continue
        vigente_total = round(unitario_vigente * cantidad, 2)
        snapshot_total = round(snapshot * cantidad, 2)
        if vigente_total != snapshot_total:
            cambios.append(
                {
                    "item_id": item["id"],
                    "tipo_producto": item["tipo_producto"],
                    "precio_snapshot": snapshot_total,
                    "precio_vigente": vigente_total,
                }
            )
    return {"items": items, "cambios": cambios}


async def confirmar_checkout(pasajero_id: str) -> dict:
    """RF-CAR-004 (CU-O96) — reserva cupo real (todo o nada), revalida
    precio, crea la reserva real (`<<include>>` CU-O21/O22) mapeando cada
    `carrito_items` a un `reserva_items` equivalente con el precio VIGENTE
    (nunca el snapshot ciego), y marca el carrito `convertido`.
    `es_paquete` se deriva del propio dbml v3 ("true si reserva_items
    tiene ≥2 tipo_producto distintos") — este checkout no aplica el
    descuento comercial de Paquetes (RF-PAQ-002), eso es responsabilidad
    exclusiva de ese módulo, con su propio flujo de construcción.

    Cupo (2026-07-19): se verifica y reserva atómicamente aquí, no antes
    (RN-CAR, generaliza RF-VUE-005) — si algún ítem ya no tiene cupo
    suficiente, se libera todo lo reservado en este mismo intento y se
    aborta sin crear ninguna reserva (`CupoInsuficiente`)."""
    carrito_repo = CarritoRepository()
    reservas_repo = ReservasRepository()

    carrito = await carrito_repo.carrito_de_trabajo(pasajero_id)
    if carrito is None:
        raise CarritoVacio()

    items = await carrito_repo.items_de_carrito(carrito["id"])
    if not items:
        raise CarritoVacio()

    reservados: list[tuple[dict, int]] = []
    fallidos: list[str] = []
    for item in items:
        cantidad = int(item.get("cantidad") or 1)
        if await carrito_repo.reservar_cupo(item["tipo_producto"], item, cantidad):
            reservados.append((item, cantidad))
        else:
            fallidos.append(item["id"])

    if fallidos:
        for item, cantidad in reservados:
            await carrito_repo.liberar_cupo_item(item["tipo_producto"], item, cantidad)
        raise CupoInsuficiente(fallidos)

    ahora = datetime.datetime.now(datetime.timezone.utc)
    ahora_iso = ahora.strftime("%Y-%m-%d %H:%M:%S.000Z")
    minutos = await _minutos_expiracion(reservas_repo)
    expiracion_iso = (ahora + datetime.timedelta(minutes=minutos)).strftime("%Y-%m-%d %H:%M:%S.000Z")

    precios_vigentes: dict[str, float] = {}
    total = 0.0
    tipos_distintos: set[str] = set()
    for item in items:
        cantidad = item.get("cantidad") or 1
        unitario_vigente = await carrito_repo.precio_vigente(item["tipo_producto"], item)
        precio_unitario = unitario_vigente if unitario_vigente is not None else (item.get("precio_snapshot") or 0.0)
        precios_vigentes[item["id"]] = round(precio_unitario * cantidad, 2)
        total += precios_vigentes[item["id"]]
        tipos_distintos.add(item["tipo_producto"])

    reserva = await reservas_repo.crear_reserva(
        {
            "codigo_reserva": _generar_codigo_reserva(),
            "pasajero_titular_id": pasajero_id,
            "canal": "autoservicio",
            "estado": "pendiente_pago",
            "es_paquete": len(tipos_distintos) >= 2,
            "total_pagar": round(total, 2),
            "fecha_reserva": ahora_iso,
            "fecha_expiracion_pago": expiracion_iso,
        }
    )

    for item in items:
        item_data = {
            "reserva_id": reserva["id"],
            "tipo_producto": item["tipo_producto"],
            "precio_final": precios_vigentes[item["id"]],
            "cantidad": item.get("cantidad") or 1,
            "estado_item": "pendiente",
        }
        if item.get("modalidad_pago"):
            item_data["modalidad_pago"] = item["modalidad_pago"]
        for campo in ("fecha_inicio", "fecha_fin", "unidades"):
            if item.get(campo) is not None:
                item_data[campo] = item[campo]
        for campo in _CAMPOS_ID_POR_TIPO[item["tipo_producto"]]:
            if item.get(campo):
                item_data[campo] = item[campo]
        await reservas_repo.crear_item(item_data)

    await carrito_repo.actualizar_carrito(carrito["id"], {"estado": "convertido", "fecha_ultima_actividad": ahora_iso})

    return reserva
