"""WP-15 (auditoría de WorkPanels, 2026-08-01) — panel de solo lectura de
Pagos y Facturas, antes inexistente (solo había `/backoffice/pagos-diferidos`,
angosto a un único caso). Sin acciones de escritura — según lo definido en
priorización."""

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository


async def _enriquecer_con_reserva(
    filas: list[dict], codigo_reserva: str | None, nombre_pasajero: str | None
) -> list[dict]:
    reservas_repo = ReservasRepository()
    pasajeros_repo = PasajerosRepository()
    cache_reservas: dict[str, dict | None] = {}
    cache_nombres: dict[str, str] = {}

    async def _reserva_de(reserva_id: str) -> dict | None:
        if reserva_id not in cache_reservas:
            cache_reservas[reserva_id] = await reservas_repo.obtener_reserva(reserva_id)
        return cache_reservas[reserva_id]

    async def _nombre_de(pasajero_id: str) -> str:
        if pasajero_id not in cache_nombres:
            pasajero = await pasajeros_repo.obtener_pasajero(pasajero_id)
            usuario = await pasajeros_repo.usuario_por_id(pasajero["usuario_id"]) if pasajero else None
            cache_nombres[pasajero_id] = usuario.get("nombre_completo", "") if usuario else ""
        return cache_nombres[pasajero_id]

    termino_codigo = codigo_reserva.lower() if codigo_reserva else None
    termino_nombre = nombre_pasajero.lower() if nombre_pasajero else None

    salida = []
    for fila in filas:
        reserva = await _reserva_de(fila["reserva_id"])
        codigo = reserva.get("codigo_reserva") if reserva else None
        nombre = await _nombre_de(reserva["pasajero_titular_id"]) if reserva else ""

        if termino_codigo and termino_codigo not in (codigo or "").lower():
            continue
        if termino_nombre and termino_nombre not in nombre.lower():
            continue

        salida.append({**fila, "codigo_reserva": codigo or "—", "pasajero_nombre": nombre or "—"})
    return salida


async def listar_pagos_backoffice(
    estado: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    codigo_reserva: str | None = None,
    nombre_pasajero: str | None = None,
) -> list[dict]:
    repo = FacturacionRepository()
    pagos = await repo.listar_pagos(estado=estado or None, desde=desde or None, hasta=hasta or None)
    return await _enriquecer_con_reserva(pagos, codigo_reserva, nombre_pasajero)


async def listar_facturas_backoffice(
    desde: str | None = None,
    hasta: str | None = None,
    codigo_reserva: str | None = None,
    nombre_pasajero: str | None = None,
) -> list[dict]:
    repo = FacturacionRepository()
    facturas = await repo.listar_facturas(desde=desde or None, hasta=hasta or None)
    return await _enriquecer_con_reserva(facturas, codigo_reserva, nombre_pasajero)


async def listar_reembolsos_backoffice(
    estado: str | None = None,
    motivo: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    tipo_producto: str | None = None,
) -> list[dict]:
    """IS-24 (auditoría de informes simples, sesión 2026-08-01) — reusa
    `_enriquecer_con_reserva` (código + nombre de pasajero) igual que Pagos/
    Facturas. `tipo_producto` es distinto: un reembolso no tiene tipo propio
    (es de la reserva completa), así que filtra a reservas que tengan al
    menos un `reserva_item` de ese tipo — la reserva puede ser un paquete
    con más de un tipo."""
    repo = FacturacionRepository()
    reembolsos = await repo.listar_reembolsos(estado=estado or None, motivo=motivo or None, desde=desde or None, hasta=hasta or None)
    salida = await _enriquecer_con_reserva(reembolsos, None, None)

    if tipo_producto:
        reservas_repo = ReservasRepository()
        cache_tipos: dict[str, set[str]] = {}
        filtrados = []
        for r in salida:
            reserva_id = r["reserva_id"]
            if reserva_id not in cache_tipos:
                items = await reservas_repo.items_de_reserva(reserva_id)
                cache_tipos[reserva_id] = {i.get("tipo_producto") for i in items}
            if tipo_producto in cache_tipos[reserva_id]:
                filtrados.append(r)
        salida = filtrados

    return salida
