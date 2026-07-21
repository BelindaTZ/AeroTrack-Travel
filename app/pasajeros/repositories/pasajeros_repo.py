from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class PasajerosRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── pasajeros ─────────────────────────────────────────────────────
    async def pasajero_de_usuario(self, usuario_id: str) -> dict | None:
        return await self._client.get_first("pasajeros", f'usuario_id="{usuario_id}"')

    async def obtener_pasajero(self, pasajero_id: str) -> dict | None:
        try:
            return await self._client.get_record("pasajeros", pasajero_id)
        except PocketBaseError:
            return None

    async def actualizar_contacto(self, pasajero_id: str, data: dict) -> dict:
        return await self._client.update_record("pasajeros", pasajero_id, data)

    async def buscar_pasajeros(self, termino: str) -> list[dict]:
        safe = termino.replace('"', '\\"')
        resultado = await self._client.list_records(
            "pasajeros",
            {
                "filter": f'(telefono~"{safe}" || contacto_emergencia~"{safe}")',
                "perPage": 100,
                "expand": "usuario_id",
            },
        )
        return resultado["items"]

    # ── usuarios (lectura) ────────────────────────────────────────────
    async def usuario_por_id(self, usuario_id: str) -> dict | None:
        try:
            return await self._client.get_record("usuarios", usuario_id)
        except PocketBaseError:
            return None

    async def buscar_usuarios(self, termino: str) -> list[dict]:
        safe = termino.replace('"', '\\"')
        resultado = await self._client.list_records(
            "usuarios",
            {
                "filter": f'nombre_completo~"{safe}" || email~"{safe}"',
                "perPage": 100,
            },
        )
        return resultado["items"]

    # ── reservas (lectura) ────────────────────────────────────────────
    async def reservas_de_pasajero(self, pasajero_id: str, estado: str | None = None) -> list[dict]:
        """`fecha_desde`/`fecha_hasta` NO se filtran aquí: son rango de fecha
        de *vuelo*, y `fecha_salida` vive en `vuelos_catalogo`, no en
        `reservas` — el filtro por rango de fecha se aplica en el servicio,
        una vez resuelto el vuelo de cada reserva."""
        filtros = [f'pasajero_titular_id="{pasajero_id}"']
        if estado:
            filtros.append(f'estado="{estado}"')
        filter_str = " && ".join(filtros)
        resultado = await self._client.list_records(
            "reservas",
            {
                "filter": filter_str,
                "sort": "-created",
                "perPage": 100,
                "expand": "vuelo_id",
            },
        )
        return resultado["items"]