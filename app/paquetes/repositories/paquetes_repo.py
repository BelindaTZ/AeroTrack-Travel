"""Consultas de Paquetes — dueño de `tipos_paquete_descuento` (única
colección propia, ver `paquetes-spec.md`: un paquete no tiene catálogo
propio, es una reserva con ≥2 tipo_producto en `reserva_items`)."""

from app.shared.pocketbase_client import PocketBaseClient, get_pocketbase_client


class PaquetesRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    async def descuento_por_combinacion(self, combinacion: str) -> dict | None:
        safe = combinacion.replace('"', '\\"')
        return await self._client.get_first(
            "tipos_paquete_descuento", f'combinacion="{safe}" && activo=true'
        )

    async def listar_combinaciones_activas(self) -> list[dict]:
        """Para la sección de Paquetes (`GET /paquetes`) — qué combinaciones
        de descuento existen hoy, para que un pasajero con intención de
        ahorrar vea las opciones antes de armar nada."""
        resultado = await self._client.list_records(
            "tipos_paquete_descuento", {"filter": "activo=true", "sort": "-porcentaje_descuento", "perPage": 50}
        )
        return resultado["items"]

    # ── CU-T14 — gestión backoffice del catálogo completo (activas e
    # inactivas), a diferencia de `listar_combinaciones_activas` de arriba.
    async def listar_todas_combinaciones(self) -> list[dict]:
        resultado = await self._client.list_records(
            "tipos_paquete_descuento", {"sort": "combinacion", "perPage": 50}
        )
        return resultado["items"]

    async def crear_combinacion(self, combinacion: str, porcentaje_descuento: float, activo: bool) -> dict:
        return await self._client.create_record(
            "tipos_paquete_descuento",
            {"combinacion": combinacion, "porcentaje_descuento": porcentaje_descuento, "activo": activo},
        )

    async def actualizar_combinacion(self, combinacion_id: str, porcentaje_descuento: float, activo: bool) -> dict:
        return await self._client.update_record(
            "tipos_paquete_descuento",
            combinacion_id,
            {"porcentaje_descuento": porcentaje_descuento, "activo": activo},
        )
