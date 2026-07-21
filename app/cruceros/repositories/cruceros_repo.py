"""Consultas de Cruceros sobre `navieras`, `barcos`, `cruceros_catalogo`,
`cruceros_camarotes_tarifa` en PocketBase."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class CrucerosRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── navieras ─────────────────────────────────────────────────────
    async def naviera_por_slug(self, slug: str) -> dict | None:
        return await self._client.get_first("navieras", f'slug_proveedor="{slug}"')

    async def crear_naviera(self, data: dict) -> dict:
        return await self._client.create_record("navieras", data)

    async def actualizar_naviera(self, naviera_id: str, data: dict) -> dict:
        return await self._client.update_record("navieras", naviera_id, data)

    async def obtener_naviera(self, naviera_id: str) -> dict | None:
        try:
            return await self._client.get_record("navieras", naviera_id)
        except PocketBaseError:
            return None

    async def listar_navieras(self) -> list[dict]:
        resultado = await self._client.list_records("navieras", {"perPage": 100})
        return resultado["items"]

    # ── barcos ───────────────────────────────────────────────────────
    async def barco_por_naviera_y_nombre(self, naviera_id: str, nombre: str) -> dict | None:
        safe = nombre.replace('"', '\\"')
        return await self._client.get_first("barcos", f'naviera_id="{naviera_id}" && nombre="{safe}"')

    async def crear_barco(self, data: dict) -> dict:
        return await self._client.create_record("barcos", data)

    async def obtener_barco(self, barco_id: str) -> dict | None:
        try:
            return await self._client.get_record("barcos", barco_id)
        except PocketBaseError:
            return None

    # ── cruceros_catalogo ────────────────────────────────────────────
    async def crucero_por_fuente_cruise_id(self, fuente_cruise_id: str) -> dict | None:
        return await self._client.get_first("cruceros_catalogo", f'fuente_cruise_id="{fuente_cruise_id}"')

    async def crear_crucero(self, data: dict) -> dict:
        return await self._client.create_record("cruceros_catalogo", data)

    async def actualizar_crucero(self, crucero_id: str, data: dict) -> dict:
        return await self._client.update_record("cruceros_catalogo", crucero_id, data)

    async def obtener_crucero(self, crucero_id: str) -> dict | None:
        try:
            return await self._client.get_record("cruceros_catalogo", crucero_id)
        except PocketBaseError:
            return None

    async def listar_cruceros(self) -> list[dict]:
        """Catálogo completo — se filtra en Python (RF-CRU-001: destino
        vive en `itinerario_puertos`, un JSON array, no un campo de texto
        indexable con `~`; el volumen real del catálogo es pequeño, así
        que traer todo y filtrar en memoria es seguro y evita depender de
        soporte incierto de PocketBase para LIKE sobre JSON)."""
        resultado = await self._client.list_records("cruceros_catalogo", {"perPage": 200})
        return resultado["items"]

    async def cruceros_de_barco(self, barco_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "cruceros_catalogo", {"filter": f'barco_id="{barco_id}"', "perPage": 50, "sort": "fecha_zarpe"}
        )
        return resultado["items"]

    # ── cruceros_camarotes_tarifa ────────────────────────────────────
    async def eliminar_camarotes_de_crucero(self, crucero_id: str) -> None:
        resultado = await self._client.list_records(
            "cruceros_camarotes_tarifa", {"filter": f'crucero_id="{crucero_id}"', "perPage": 50}
        )
        for camarote in resultado["items"]:
            await self._client.delete_record("cruceros_camarotes_tarifa", camarote["id"])

    async def crear_camarote(self, data: dict) -> dict:
        return await self._client.create_record("cruceros_camarotes_tarifa", data)

    async def camarotes_de_crucero(self, crucero_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "cruceros_camarotes_tarifa", {"filter": f'crucero_id="{crucero_id}"', "perPage": 50, "sort": "precio_por_persona"}
        )
        return resultado["items"]

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
