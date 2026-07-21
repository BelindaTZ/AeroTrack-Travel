"""Consultas de Disrupciones sobre `disrupciones` y `notificaciones` en
PocketBase — único módulo dueño de estas dos colecciones."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class DisrupcionesRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── disrupciones ─────────────────────────────────────────────────
    async def crear_disrupcion(self, data: dict) -> dict:
        return await self._client.create_record("disrupciones", data)

    async def obtener_disrupcion(self, disrupcion_id: str) -> dict | None:
        try:
            return await self._client.get_record("disrupciones", disrupcion_id)
        except PocketBaseError:
            return None

    async def disrupciones_de_vuelo_y_tipo(self, vuelo_id: str, tipo_cambio: str) -> list[dict]:
        resultado = await self._client.list_records(
            "disrupciones",
            {
                "filter": f'vuelo_id="{vuelo_id}" && tipo_cambio="{tipo_cambio}" && estado="activa"',
                "perPage": 50,
            },
        )
        return resultado["items"]

    async def actualizar_disrupcion(self, disrupcion_id: str, data: dict) -> dict:
        return await self._client.update_record("disrupciones", disrupcion_id, data)

    # ── notificaciones ───────────────────────────────────────────────
    async def crear_notificacion(self, data: dict) -> dict:
        return await self._client.create_record("notificaciones", data)

    async def obtener_notificacion(self, notificacion_id: str) -> dict | None:
        try:
            return await self._client.get_record("notificaciones", notificacion_id)
        except PocketBaseError:
            return None

    async def actualizar_notificacion(self, notificacion_id: str, data: dict) -> dict:
        return await self._client.update_record("notificaciones", notificacion_id, data)

    async def notificaciones_de_disrupcion_y_pasajero(
        self, disrupcion_id: str, pasajero_id: str
    ) -> list[dict]:
        resultado = await self._client.list_records(
            "notificaciones",
            {
                "filter": f'disrupcion_id="{disrupcion_id}" && pasajero_id="{pasajero_id}"',
                "perPage": 10,
            },
        )
        return resultado["items"]

    async def notificaciones_de_pasajero(
        self,
        pasajero_id: str,
        canal: str | None = None,
        estado_envio: str | None = None,
    ) -> list[dict]:
        filtros = [f'pasajero_id="{pasajero_id}"']
        if canal:
            filtros.append(f'canal="{canal}"')
        if estado_envio:
            filtros.append(f'estado_envio="{estado_envio}"')
        resultado = await self._client.list_records(
            "notificaciones",
            {"filter": " && ".join(filtros), "sort": "-created", "perPage": 100},
        )
        return resultado["items"]

    async def notificaciones_fallidas(self) -> list[dict]:
        resultado = await self._client.list_records(
            "notificaciones",
            {"filter": 'estado_envio="fallido"', "sort": "-created", "perPage": 200},
        )
        return resultado["items"]

    async def listar_notificaciones(self, filtro: str | None = None) -> list[dict]:
        params = {"sort": "-created", "perPage": 200}
        if filtro:
            params["filter"] = filtro
        resultado = await self._client.list_records("notificaciones", params)
        return resultado["items"]

    # ── configuración ────────────────────────────────────────────────
    async def config(self, clave: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        return await self._client.get_first("configuracion_sistema", f'clave="{safe}"')

    async def actualizar_config(self, clave: str, valor: str) -> dict:
        registro = await self.config(clave)
        if registro is None:
            raise RuntimeError(f"configuracion_sistema.{clave} no está sembrado")
        return await self._client.update_record("configuracion_sistema", registro["id"], {"valor": valor})
