"""Consultas de Autos sobre `autos_catalogo` en PocketBase — única
colección propia de este módulo (a diferencia de Hoteles, sin tabla de
tarifas ni de reseñas separadas, ver dbml v3)."""

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class AutosRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    async def crear_auto(self, data: dict) -> dict:
        return await self._client.create_record("autos_catalogo", data)

    async def obtener_auto(self, auto_id: str) -> dict | None:
        try:
            return await self._client.get_record("autos_catalogo", auto_id)
        except PocketBaseError:
            return None

    async def eliminar_ofertas_de_ciudad(self, ciudad_recogida: str, proveedor_agregador: str) -> None:
        """RN-AUT-001: los precios de estas APIs son point-in-time — cada
        corrida reemplaza el snapshot anterior de esa ciudad/agregador, no
        acumula ofertas viejas junto a las nuevas."""
        safe = ciudad_recogida.replace('"', '\\"')
        resultado = await self._client.list_records(
            "autos_catalogo",
            {"filter": f'ciudad_recogida="{safe}" && proveedor_agregador="{proveedor_agregador}"', "perPage": 200},
        )
        for auto in resultado["items"]:
            # `autos_disponibilidad` primero — sus filas quedarían huérfanas
            # si se borrara el auto antes (ver pb_schema_autos.py).
            await self.eliminar_disponibilidad_de_auto(auto["id"])
            await self._client.delete_record("autos_catalogo", auto["id"])

    async def buscar_por_ciudad(self, ciudad: str) -> list[dict]:
        # "~" es case-insensitive/substring en PocketBase — el pasajero no
        # tiene por qué escribir la ciudad con la misma capitalización con
        # la que la sembró el catálogo (RF-AUT-001).
        safe = ciudad.replace('"', '\\"')
        resultado = await self._client.list_records(
            "autos_catalogo", {"filter": f'ciudad_recogida~"{safe}"', "perPage": 100}
        )
        return resultado["items"]

    async def ciudades_disponibles(self) -> list[str]:
        resultado = await self._client.list_records(
            "autos_catalogo", {"perPage": 200, "fields": "ciudad_recogida"}
        )
        return sorted({item["ciudad_recogida"] for item in resultado["items"] if item.get("ciudad_recogida")})

    # ── autos_disponibilidad (RF-AUT-004, cupo real por día) ────────────
    async def eliminar_disponibilidad_de_auto(self, auto_id: str) -> None:
        resultado = await self._client.list_records(
            "autos_disponibilidad", {"filter": f'auto_id="{auto_id}"', "perPage": 500}
        )
        for fila in resultado["items"]:
            await self._client.delete_record("autos_disponibilidad", fila["id"])

    async def crear_disponibilidad(self, data: dict) -> dict:
        return await self._client.create_record("autos_disponibilidad", data)

    async def disponibilidad_de_auto(self, auto_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "autos_disponibilidad", {"filter": f'auto_id="{auto_id}"', "perPage": 200}
        )
        return resultado["items"]

    # ── configuración ────────────────────────────────────────────────
    async def config(self, clave: str) -> str | None:
        safe = clave.replace('"', '\\"')
        registro = await self._client.get_first("configuracion_sistema", f'clave="{safe}"')
        return registro["valor"] if registro else None

    # ── Reservas (lectura, CU-T11) — reserva_items es dueño de Reservas,
    #    OPERACIONAL en MinIO — ver plan de migración. ──────────────────
    async def items_de_auto_desde(self, fecha_iso: str) -> list[dict]:
        items = await moc.listar_todos("reserva_items")
        return [
            i for i in items
            if i.get("tipo_producto") == "auto" and (i.get("created") or "") >= fecha_iso
        ]

    # ── Integraciones (sincronizaciones_log) — se escribe, no es dueño ──
    async def fuente_por_nombre(self, nombre: str) -> dict | None:
        safe = nombre.replace('"', '\\"')
        return await self._client.get_first("fuentes_datos_externas", f'nombre="{safe}"')

    async def crear_log_sincronizacion(self, data: dict) -> dict:
        return await self._client.create_record("sincronizaciones_log", data)
