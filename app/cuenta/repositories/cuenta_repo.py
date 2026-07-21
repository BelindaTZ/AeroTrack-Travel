"""Consultas de Cuenta/Mis Viajes sobre `favoritos`, `viajes_personalizados`,
`busquedas_recientes` (lectura — la escritura es de cada módulo de producto,
RN-CTA-001) y `programa_beneficios_movimientos`/`programa_beneficios_niveles`
en PocketBase. Lee `reservas`/`reserva_items` (propiedad de Reservas) pero
nunca escribe ahí."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class CuentaRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── favoritos ────────────────────────────────────────────────────
    async def crear_favorito(self, pasajero_id: str, tipo: str, producto_ref: str, fecha_iso: str) -> dict:
        return await self._client.create_record(
            "favoritos",
            {
                "pasajero_id": pasajero_id,
                "tipo": tipo,
                "producto_ref": producto_ref,
                "fecha_guardado": fecha_iso,
            },
        )

    async def listar_favoritos(self, pasajero_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "favoritos", {"filter": f'pasajero_id="{pasajero_id}"', "sort": "-fecha_guardado", "perPage": 200}
        )
        return resultado["items"]

    async def obtener_favorito(self, favorito_id: str) -> dict | None:
        try:
            return await self._client.get_record("favoritos", favorito_id)
        except PocketBaseError:
            return None

    async def eliminar_favorito(self, favorito_id: str) -> None:
        await self._client.delete_record("favoritos", favorito_id)

    # ── viajes_personalizados ────────────────────────────────────────
    async def crear_viaje_personalizado(self, pasajero_id: str, nombre: str, descripcion: str | None) -> dict:
        return await self._client.create_record(
            "viajes_personalizados",
            {"pasajero_id": pasajero_id, "nombre": nombre, "descripcion": descripcion or ""},
        )

    async def listar_viajes_personalizados(self, pasajero_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "viajes_personalizados", {"filter": f'pasajero_id="{pasajero_id}"', "sort": "-created", "perPage": 200}
        )
        return resultado["items"]

    async def eliminar_viaje_personalizado(self, viaje_id: str) -> None:
        await self._client.delete_record("viajes_personalizados", viaje_id)

    async def obtener_viaje_personalizado(self, viaje_id: str) -> dict | None:
        try:
            return await self._client.get_record("viajes_personalizados", viaje_id)
        except PocketBaseError:
            return None

    # ── busquedas_recientes (lectura — RN-CTA-001: cada módulo de
    #    producto es quien escribe, ver app.shared.busqueda_reciente) ──
    async def listar_busquedas_recientes(self, pasajero_id: str, limite: int = 20) -> list[dict]:
        resultado = await self._client.list_records(
            "busquedas_recientes",
            {"filter": f'pasajero_id="{pasajero_id}"', "sort": "-fecha", "perPage": limite},
        )
        return resultado["items"]

    async def obtener_busqueda_reciente(self, busqueda_id: str) -> dict | None:
        try:
            return await self._client.get_record("busquedas_recientes", busqueda_id)
        except PocketBaseError:
            return None

    # ── programa de beneficios ───────────────────────────────────────
    async def movimientos_de_pasajero(self, pasajero_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "programa_beneficios_movimientos",
            {"filter": f'pasajero_id="{pasajero_id}"', "sort": "-fecha", "perPage": 500},
        )
        return resultado["items"]

    async def niveles_programa_beneficios(self) -> list[dict]:
        resultado = await self._client.list_records(
            "programa_beneficios_niveles", {"sort": "puntos_minimos", "perPage": 50}
        )
        return resultado["items"]
