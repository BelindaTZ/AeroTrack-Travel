"""Consultas de Carrito sobre `carritos`/`carrito_items` en PocketBase,
más lectura de precio vigente y reserva/liberación de cupo en las 5
colecciones dueñas de catálogo (RN-CAR-001 precio; cupo generalizado
2026-07-19 vía `app.shared.cupo_service`, mismo mecanismo que ya usaba
Vuelos en solitario) — nunca escritura directa de precio, cupo siempre a
través del servicio compartido para no perder atomicidad."""

from app.shared.catalogo_producto import CATALOGO_POR_TIPO
from app.shared.cupo_service import liberar_cupo, verificar_y_reservar_cupo
from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class CarritoRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── carritos ─────────────────────────────────────────────────────
    async def carrito_activo_de_pasajero(self, pasajero_id: str) -> dict | None:
        return await self._client.get_first(
            "carritos", f'pasajero_id="{pasajero_id}" && estado="activo"'
        )

    async def crear_carrito(self, data: dict) -> dict:
        return await self._client.create_record("carritos", data)

    async def actualizar_carrito(self, carrito_id: str, data: dict) -> dict:
        return await self._client.update_record("carritos", carrito_id, data)

    async def obtener_carrito(self, carrito_id: str) -> dict | None:
        try:
            return await self._client.get_record("carritos", carrito_id)
        except PocketBaseError:
            return None

    # ── carrito_items ────────────────────────────────────────────────
    async def crear_item(self, data: dict) -> dict:
        return await self._client.create_record("carrito_items", data)

    async def eliminar_item(self, item_id: str) -> None:
        await self._client.delete_record("carrito_items", item_id)

    async def obtener_item(self, item_id: str) -> dict | None:
        try:
            return await self._client.get_record("carrito_items", item_id)
        except PocketBaseError:
            return None

    async def items_de_carrito(self, carrito_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "carrito_items", {"filter": f'carrito_id="{carrito_id}"', "perPage": 50}
        )
        return resultado["items"]

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
    # siempre vía app.shared.cupo_service para conservar atomicidad ────
    async def reservar_cupo(self, tipo_producto: str, item: dict, cantidad: int = 1) -> bool:
        """True si hay cupo suficiente (o el tipo de producto no modela
        cupo) — en ese caso ya quedó decrementado. False si no alcanza,
        sin tocar nada."""
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

    async def liberar_cupo_item(self, tipo_producto: str, item: dict, cantidad: int = 1) -> None:
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
