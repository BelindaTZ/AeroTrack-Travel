"""`carritos`/`carrito_items` son OPERACIONAL — migrados a MinIO como par
(carrito_items depende de carritos, confirmado en el barrido de relation
fields de la sesión). Precio vigente y cupo siguen contra las 5
colecciones STAGING dueñas de catálogo en PocketBase (RN-CAR-001 precio;
cupo vía `app.shared.cupo_service`) — el split de `cupos_disponibles` a
tier operacional en MinIO queda fuera de alcance de esta fase (ver nota en
el plan de migración sobre `asientos_vuelo`, mismo criterio: no se toca
hasta su propia fase dedicada)."""

import datetime

from app.shared import minio_operational_client as moc
from app.shared import cupo_rango_service
from app.shared.catalogo_producto import CATALOGO_POR_TIPO
from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client

ENTIDAD_CARRITOS = "carritos"
ENTIDAD_ITEMS = "carrito_items"


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


class CarritoRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── carritos ─────────────────────────────────────────────────────
    async def carrito_de_trabajo(self, pasajero_id: str) -> dict | None:
        """Carrito vigente del pasajero para ver/agregar/pagar — incluye uno
        `abandonado` (RN-CAR-T01: solo `convertido` queda fuera, ese ciclo
        ya cerró). Volver a interactuar con un carrito `abandonado` es
        exactamente la señal de recuperación que persigue CU-T27, así que
        se reactiva a `activo` aquí mismo, en el único punto de entrada
        real — sin esto, un carrito abandonado nunca podría completar
        checkout ni contar como recuperado."""
        carritos = await moc.listar_todos(ENTIDAD_CARRITOS)
        carrito = next(
            (
                c for c in carritos
                if c.get("pasajero_id") == pasajero_id and c.get("estado") in ("activo", "abandonado")
            ),
            None,
        )
        if carrito is None:
            return None
        if carrito["estado"] == "abandonado":
            carrito = await self.actualizar_carrito(carrito["id"], {"estado": "activo"})
        return carrito

    async def carritos_activos_inactivos_desde(self, limite_iso: str) -> list[dict]:
        carritos = await moc.listar_todos(ENTIDAD_CARRITOS)
        return [
            c for c in carritos
            if c.get("estado") == "activo" and (c.get("fecha_ultima_actividad") or "") <= limite_iso
        ]

    async def carritos_abandonados_desde(self, fecha_iso: str) -> list[dict]:
        carritos = await moc.listar_todos(ENTIDAD_CARRITOS)
        return [
            c for c in carritos
            if c.get("fue_abandonado") and (c.get("fecha_marcado_abandonado") or "") >= fecha_iso
        ]

    async def config(self, clave: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        return await self._client.get_first("configuracion_sistema", f'clave="{safe}"')

    async def actualizar_config(self, clave: str, valor: str, usuario_id: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        registro = await self._client.get_first("configuracion_sistema", f'clave="{safe}"')
        if registro is None:
            return None
        return await self._client.update_record(
            "configuracion_sistema", registro["id"], {"valor": valor, "modificado_por": usuario_id}
        )

    async def crear_carrito(self, data: dict) -> dict:
        id_ = moc.generar_id()
        registro = {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}
        return await moc.crear(ENTIDAD_CARRITOS, id_, registro)

    async def actualizar_carrito(self, carrito_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_CARRITOS, carrito_id, _mutar)

    async def obtener_carrito(self, carrito_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_CARRITOS, carrito_id)

    # ── carrito_items ────────────────────────────────────────────────
    async def crear_item(self, data: dict) -> dict:
        id_ = moc.generar_id()
        registro = {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}
        return await moc.crear(ENTIDAD_ITEMS, id_, registro)

    async def eliminar_item(self, item_id: str) -> None:
        await moc.eliminar(ENTIDAD_ITEMS, item_id)

    async def obtener_item(self, item_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_ITEMS, item_id)

    async def items_de_carrito(self, carrito_id: str) -> list[dict]:
        items = await moc.listar_todos(ENTIDAD_ITEMS)
        return [i for i in items if i.get("carrito_id") == carrito_id]

    async def listar_todos_items(self) -> list[dict]:
        """ETL comercial (Fase B, sesión 2026-08-02) — todos los
        `carrito_items` sin acotar a un carrito, para el funnel de
        conversión búsqueda→carrito→checkout→reserva."""
        return await moc.listar_todos(ENTIDAD_ITEMS)

    async def listar_todos_carritos(self) -> list[dict]:
        return await moc.listar_todos(ENTIDAD_CARRITOS)

    # ── revalidación de precio vigente (RN-CAR-001) ─────────────────
    async def precio_vigente(self, tipo_producto: str, item: dict) -> float | None:
        info = CATALOGO_POR_TIPO.get(tipo_producto)
        if info is None:
            return None
        coleccion, campo_precio, campo_id, _ = info
        registro_id = item.get(campo_id)
        if not registro_id:
            return None
        try:
            registro = await self._client.get_record(coleccion, registro_id)
        except PocketBaseError:
            return None
        return registro.get(campo_precio)

    # ── reserva/liberación de cupo (generaliza RF-VUE-005 al resto de
    # verticales) — nunca se decrementa/incrementa el dato directo aquí,
    # siempre vía app.shared.cupo_service para conservar atomicidad.
    # Hotel/Auto delegan a cupo_rango_service (una fila por noche/día del
    # rango, ver ese módulo) — dispatchers finos, sin lógica propia. ─────
    async def reservar_cupo(self, tipo_producto: str, item: dict, cantidad: int = 1) -> bool:
        """True si hay cupo suficiente (o el tipo de producto no modela
        cupo) — en ese caso ya quedó decrementado. False si no alcanza,
        sin tocar nada."""
        return await cupo_rango_service.reservar_cupo_item(tipo_producto, item, cantidad)

    async def liberar_cupo_item(self, tipo_producto: str, item: dict, cantidad: int = 1) -> None:
        await cupo_rango_service.liberar_cupo_item(tipo_producto, item, cantidad)
