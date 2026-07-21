"""Consultas de Hoteles sobre `hoteles_catalogo`, `hoteles_tarifas`,
`hoteles_resenas` en PocketBase. Este módulo es dueño de las 3 — no toca
`proveedores_comerciales` (Facturación) más allá de leer la relación
cuando existe (RNF-HOT-002)."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class HotelesRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── hoteles_catalogo ─────────────────────────────────────────────
    async def hotel_por_fuente_entity_url(self, url: str) -> dict | None:
        safe = url.replace('"', '\\"')
        return await self._client.get_first("hoteles_catalogo", f'fuente_entity_url="{safe}"')

    async def crear_hotel(self, data: dict) -> dict:
        return await self._client.create_record("hoteles_catalogo", data)

    async def actualizar_hotel(self, hotel_id: str, data: dict) -> dict:
        return await self._client.update_record("hoteles_catalogo", hotel_id, data)

    async def obtener_hotel(self, hotel_id: str) -> dict | None:
        try:
            return await self._client.get_record("hoteles_catalogo", hotel_id)
        except PocketBaseError:
            return None

    async def buscar_por_ciudad(self, ciudad: str) -> list[dict]:
        safe = ciudad.replace('"', '\\"')
        resultado = await self._client.list_records(
            "hoteles_catalogo", {"filter": f'ciudad~"{safe}"', "perPage": 100}
        )
        return resultado["items"]

    async def ciudades_disponibles(self) -> list[str]:
        resultado = await self._client.list_records("hoteles_catalogo", {"perPage": 200, "fields": "ciudad"})
        return sorted({item["ciudad"] for item in resultado["items"] if item.get("ciudad")})

    # ── hoteles_tarifas ──────────────────────────────────────────────
    async def eliminar_tarifas_de_hotel(self, hotel_id: str) -> None:
        resultado = await self._client.list_records(
            "hoteles_tarifas", {"filter": f'hotel_id="{hotel_id}"', "perPage": 100}
        )
        for tarifa in resultado["items"]:
            await self._client.delete_record("hoteles_tarifas", tarifa["id"])

    async def crear_tarifa(self, data: dict) -> dict:
        return await self._client.create_record("hoteles_tarifas", data)

    async def tarifas_de_hotel(self, hotel_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "hoteles_tarifas", {"filter": f'hotel_id="{hotel_id}"', "perPage": 50}
        )
        return resultado["items"]

    # ── hoteles_resenas ──────────────────────────────────────────────
    async def eliminar_resenas_de_hotel(self, hotel_id: str) -> None:
        resultado = await self._client.list_records(
            "hoteles_resenas", {"filter": f'hotel_id="{hotel_id}"', "perPage": 100}
        )
        for resena in resultado["items"]:
            await self._client.delete_record("hoteles_resenas", resena["id"])

    async def crear_resena(self, data: dict) -> dict:
        return await self._client.create_record("hoteles_resenas", data)

    async def resenas_de_hotel(self, hotel_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "hoteles_resenas", {"filter": f'hotel_id="{hotel_id}"', "perPage": 50}
        )
        return resultado["items"]

    # ── cargos_locales_destino (RF-HOT-008, RN-HOT-003 — sí es dueño de
    # la importación del CSV, aunque la tabla no tenga otro escritor) ──
    async def cargos_locales_de_ciudad(self, ciudad: str) -> list[dict]:
        safe = ciudad.replace('"', '\\"')
        resultado = await self._client.list_records(
            "cargos_locales_destino", {"filter": f'ciudad="{safe}" && activo=true', "perPage": 10}
        )
        return resultado["items"]

    async def cargo_local_por_ciudad_pais(self, ciudad: str, pais: str) -> dict | None:
        safe_ciudad = ciudad.replace('"', '\\"')
        safe_pais = pais.replace('"', '\\"')
        return await self._client.get_first(
            "cargos_locales_destino", f'ciudad="{safe_ciudad}" && pais="{safe_pais}"'
        )

    async def crear_cargo_local(self, data: dict) -> dict:
        return await self._client.create_record("cargos_locales_destino", data)

    async def actualizar_cargo_local(self, cargo_id: str, data: dict) -> dict:
        return await self._client.update_record("cargos_locales_destino", cargo_id, data)

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
