"""Consultas de Actividades sobre `actividades_catalogo`,
`actividades_horarios`, `actividades_resenas` en PocketBase."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class ActividadesRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── actividades_catalogo ─────────────────────────────────────────
    async def actividad_por_content_id(self, content_id: str) -> dict | None:
        safe = content_id.replace('"', '\\"')
        return await self._client.get_first("actividades_catalogo", f'fuente_content_id="{safe}"')

    async def crear_actividad(self, data: dict) -> dict:
        return await self._client.create_record("actividades_catalogo", data)

    async def actualizar_actividad(self, actividad_id: str, data: dict) -> dict:
        return await self._client.update_record("actividades_catalogo", actividad_id, data)

    async def obtener_actividad(self, actividad_id: str) -> dict | None:
        try:
            return await self._client.get_record("actividades_catalogo", actividad_id)
        except PocketBaseError:
            return None

    async def buscar_por_ciudad(self, ciudad: str) -> list[dict]:
        safe = ciudad.replace('"', '\\"')
        resultado = await self._client.list_records(
            "actividades_catalogo", {"filter": f'ciudad~"{safe}"', "perPage": 100}
        )
        return resultado["items"]

    async def ciudades_disponibles(self) -> list[dict]:
        """`[{"ciudad":..., "pais":...}]`, deduplicado — `pais` viene real
        de Travel Advisor, usado en el selector de origen/destino para
        mostrar "Ciudad, País" en vez de solo el nombre de la ciudad."""
        resultado = await self._client.list_records(
            "actividades_catalogo", {"perPage": 200, "fields": "ciudad,pais"}
        )
        pares = {(item["ciudad"], item.get("pais") or "") for item in resultado["items"] if item.get("ciudad")}
        return sorted(({"ciudad": c, "pais": p} for c, p in pares), key=lambda x: x["ciudad"])

    # ── actividades_resenas ──────────────────────────────────────────
    async def resenas_de_actividad(self, actividad_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "actividades_resenas",
            {"filter": f'actividad_id="{actividad_id}"', "perPage": 50, "sort": "-fecha_resena"},
        )
        return resultado["items"]

    async def eliminar_resenas_de_actividad(self, actividad_id: str) -> None:
        resultado = await self._client.list_records(
            "actividades_resenas", {"filter": f'actividad_id="{actividad_id}"', "perPage": 100}
        )
        for resena in resultado["items"]:
            await self._client.delete_record("actividades_resenas", resena["id"])

    async def crear_resena(self, data: dict) -> dict:
        return await self._client.create_record("actividades_resenas", data)

    # ── actividades_horarios (CU-O121, disponibilidad sintética) ─────
    async def eliminar_horarios_futuros_de_actividad(self, actividad_id: str, desde_iso: str) -> None:
        resultado = await self._client.list_records(
            "actividades_horarios",
            {"filter": f'actividad_id="{actividad_id}" && fecha>="{desde_iso}"', "perPage": 200},
        )
        for horario in resultado["items"]:
            await self._client.delete_record("actividades_horarios", horario["id"])

    async def crear_horario(self, data: dict) -> dict:
        return await self._client.create_record("actividades_horarios", data)

    async def horarios_de_actividad(self, actividad_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "actividades_horarios", {"filter": f'actividad_id="{actividad_id}"', "perPage": 100, "sort": "fecha"}
        )
        return resultado["items"]

    async def obtener_horario(self, horario_id: str) -> dict | None:
        try:
            return await self._client.get_record("actividades_horarios", horario_id)
        except PocketBaseError:
            return None

    # ── configuración ────────────────────────────────────────────────
    async def config(self, clave: str) -> str | None:
        safe = clave.replace('"', '\\"')
        registro = await self._client.get_first("configuracion_sistema", f'clave="{safe}"')
        return registro["valor"] if registro else None

    # ── Integraciones (sincronizaciones_log) — se escribe, no es dueño ──
    async def fuente_por_nombre(self, nombre: str) -> dict | None:
        safe = nombre.replace('"', '\\"')
        return await self._client.get_first("fuentes_datos_externas", f'nombre="{safe}"')

    async def crear_log_sincronizacion(self, data: dict) -> dict:
        return await self._client.create_record("sincronizaciones_log", data)
