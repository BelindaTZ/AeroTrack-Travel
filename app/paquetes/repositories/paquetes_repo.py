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
