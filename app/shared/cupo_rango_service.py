"""Reserva/liberación de cupo para ítems de Hotel/Auto — a diferencia del
resto de tipos (`app.shared.cupo_service`, una fila por ítem), una
estadía/renta abarca N noches/días, cada una su propia fila en
`hoteles_disponibilidad`/`autos_disponibilidad` (ver
`app.shared.catalogo_producto.CATALOGO_RANGO_POR_TIPO`). Único punto de
verdad usado por Carrito (`confirmar_checkout`) y Reservas
(`expiracion_service`, `cancelar_reserva_service`) para estos dos tipos —
para el resto (`vuelo`/`actividad`/`crucero`), `reservar_cupo_item`/
`liberar_cupo_item` delegan sin cambios al mecanismo de una sola fila.

Gap real cerrado 2026-07-29 (ver `errores-conocidos.md`): antes de esto,
Hotel y Auto no reservaban cupo por fecha en absoluto — check-in/check-out
y recogida/devolución eran cosméticos."""

from app.shared.catalogo_producto import CATALOGO_POR_TIPO, CATALOGO_RANGO_POR_TIPO
from app.shared.cupo_service import liberar_cupo, verificar_y_reservar_cupo
from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client
from app.shared.rango_fechas import fechas_rango

TIPOS_CON_RANGO = set(CATALOGO_RANGO_POR_TIPO)


async def _filas_de_rango(coleccion: str, campo_id_padre: str, id_padre: str, fechas: list[str]) -> list[dict | None]:
    """Una entrada por fecha pedida, alineada con `fechas` — `None` si esa
    fecha no tiene fila generada (fuera de la ventana `dias_adelante` del
    módulo, ver `catalogo_service.py` de Hoteles/Autos)."""
    client = get_pocketbase_client()
    try:
        resultado = await client.list_records(
            coleccion, {"filter": f'{campo_id_padre}="{id_padre}"', "perPage": 500}
        )
    except PocketBaseError:
        return [None for _ in fechas]
    por_fecha = {fila["fecha"][:10]: fila for fila in resultado["items"]}
    return [por_fecha.get(fecha) for fecha in fechas]


async def _reservar_cupo_rango(
    coleccion: str, campo_id_padre: str, id_padre: str, campo_cupo: str,
    fecha_inicio: str, fecha_fin: str, unidades: int,
) -> bool:
    fechas = fechas_rango(fecha_inicio, fecha_fin)
    if not fechas:
        return True
    filas = await _filas_de_rango(coleccion, campo_id_padre, id_padre, fechas)
    if any(fila is None for fila in filas):
        return False

    reservadas: list[str] = []
    for fila in filas:
        if await verificar_y_reservar_cupo(coleccion, fila["id"], campo_cupo, unidades):
            reservadas.append(fila["id"])
        else:
            # PocketBase no ofrece transacciones entre filas — se revierte
            # manualmente lo ya reservado de ESTE mismo ítem antes de
            # devolver False (mismo idioma que usuarios_service.py).
            for fila_id in reservadas:
                await liberar_cupo(coleccion, fila_id, campo_cupo, unidades)
            return False
    return True


async def _liberar_cupo_rango(
    coleccion: str, campo_id_padre: str, id_padre: str, campo_cupo: str,
    fecha_inicio: str, fecha_fin: str, unidades: int,
) -> None:
    fechas = fechas_rango(fecha_inicio, fecha_fin)
    if not fechas:
        return
    filas = await _filas_de_rango(coleccion, campo_id_padre, id_padre, fechas)
    for fila in filas:
        if fila is not None:
            await liberar_cupo(coleccion, fila["id"], campo_cupo, unidades)


async def reservar_cupo_item(tipo_producto: str, item: dict, cantidad: int) -> bool:
    """`cantidad` (unidades × noches/días) se IGNORA a propósito para
    hotel/auto — usarla reservaría contra cada noche/día una cantidad que
    ya incluye el factor de noches, doble conteo. Lo que se reserva por
    fila es `item["unidades"]` (habitaciones/vehículos), una vez por cada
    fecha del rango. Para el resto de tipos, delega sin cambios al
    mecanismo de una sola fila (`CATALOGO_POR_TIPO`)."""
    if tipo_producto not in TIPOS_CON_RANGO:
        info = CATALOGO_POR_TIPO.get(tipo_producto)
        if info is None:
            return True
        coleccion, _, campo_id, campo_cupo = info
        if campo_cupo is None:
            return True
        registro_id = item.get(campo_id)
        if not registro_id:
            return True
        return await verificar_y_reservar_cupo(coleccion, registro_id, campo_cupo, cantidad)

    fecha_inicio, fecha_fin = item.get("fecha_inicio"), item.get("fecha_fin")
    if not fecha_inicio or not fecha_fin:
        return True  # ítem legado/incompleto sin rango — nada que reservar por fecha
    coleccion, campo_id_padre, campo_cupo = CATALOGO_RANGO_POR_TIPO[tipo_producto]
    id_padre = item.get(campo_id_padre)
    if not id_padre:
        return True
    unidades = int(item.get("unidades") or 1)
    return await _reservar_cupo_rango(coleccion, campo_id_padre, id_padre, campo_cupo, fecha_inicio, fecha_fin, unidades)


async def liberar_cupo_item(tipo_producto: str, item: dict, cantidad: int) -> None:
    """Inversa de `reservar_cupo_item` — mismo criterio de bifurcación."""
    if tipo_producto not in TIPOS_CON_RANGO:
        info = CATALOGO_POR_TIPO.get(tipo_producto)
        if info is None:
            return
        coleccion, _, campo_id, campo_cupo = info
        if campo_cupo is None:
            return
        registro_id = item.get(campo_id)
        if not registro_id:
            return
        await liberar_cupo(coleccion, registro_id, campo_cupo, cantidad)
        return

    fecha_inicio, fecha_fin = item.get("fecha_inicio"), item.get("fecha_fin")
    if not fecha_inicio or not fecha_fin:
        return
    coleccion, campo_id_padre, campo_cupo = CATALOGO_RANGO_POR_TIPO[tipo_producto]
    id_padre = item.get(campo_id_padre)
    if not id_padre:
        return
    unidades = int(item.get("unidades") or 1)
    await _liberar_cupo_rango(coleccion, campo_id_padre, id_padre, campo_cupo, fecha_inicio, fecha_fin, unidades)
