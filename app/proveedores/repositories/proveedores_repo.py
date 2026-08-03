"""WP-10 (auditoría de WorkPanels, 2026-07-31) — `proveedores_comerciales`
(PocketBase, catálogo/config), sembrada por `scripts/pb_schema_proveedores_
comerciales.py` y leída por Autos/Hoteles para resolver comisión pactada,
pero sin ningún panel de gestión hasta ahora."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class ProveedoresRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    async def listar(
        self, nombre: str | None = None, tipo_producto: str | None = None, estado: str | None = None
    ) -> list[dict]:
        condiciones = []
        if nombre:
            safe = nombre.replace('"', '\\"')
            condiciones.append(f'nombre~"{safe}"')
        if tipo_producto:
            condiciones.append(f'tipo_producto="{tipo_producto}"')
        if estado == "activo":
            condiciones.append("activo=true")
        elif estado == "inactivo":
            condiciones.append("activo=false")
        params: dict = {"sort": "nombre", "perPage": 200}
        if condiciones:
            params["filter"] = " && ".join(condiciones)
        resultado = await self._client.list_records("proveedores_comerciales", params)
        return resultado["items"]

    async def obtener(self, proveedor_id: str) -> dict | None:
        try:
            return await self._client.get_record("proveedores_comerciales", proveedor_id)
        except PocketBaseError:
            return None

    async def crear(self, data: dict) -> dict:
        return await self._client.create_record("proveedores_comerciales", data)

    async def actualizar(self, proveedor_id: str, data: dict) -> dict:
        return await self._client.update_record("proveedores_comerciales", proveedor_id, data)
