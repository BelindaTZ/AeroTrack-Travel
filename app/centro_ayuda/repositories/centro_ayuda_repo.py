"""Consultas de Centro de Ayuda sobre `articulos_ayuda`,
`articulo_calificaciones`, `casos_escalados` en PocketBase."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class CentroAyudaRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── articulos_ayuda ──────────────────────────────────────────────
    async def buscar_articulos(self, termino: str | None, categoria: str | None) -> list[dict]:
        condiciones = ['activo=true']
        if categoria:
            safe = categoria.replace('"', '\\"')
            condiciones.append(f'categoria="{safe}"')
        if termino:
            safe = termino.replace('"', '\\"')
            condiciones.append(f'(titulo~"{safe}" || contenido~"{safe}")')
        resultado = await self._client.list_records(
            "articulos_ayuda", {"filter": " && ".join(condiciones), "sort": "-fecha_publicacion", "perPage": 100}
        )
        return resultado["items"]

    async def obtener_articulo(self, articulo_id: str) -> dict | None:
        try:
            return await self._client.get_record("articulos_ayuda", articulo_id)
        except PocketBaseError:
            return None

    async def categorias_disponibles(self) -> list[str]:
        resultado = await self._client.list_records("articulos_ayuda", {"filter": "activo=true", "perPage": 200})
        return sorted({a["categoria"] for a in resultado["items"] if a.get("categoria")})

    async def listar_articulos_admin(self) -> list[dict]:
        """Incluye archivados — el Administrador gestiona ambos estados (RN-AYU-T01)."""
        resultado = await self._client.list_records("articulos_ayuda", {"sort": "-fecha_publicacion", "perPage": 200})
        return resultado["items"]

    async def crear_articulo(self, data: dict) -> dict:
        return await self._client.create_record("articulos_ayuda", data)

    async def actualizar_articulo(self, articulo_id: str, data: dict) -> dict:
        return await self._client.update_record("articulos_ayuda", articulo_id, data)

    # ── articulo_calificaciones ──────────────────────────────────────
    async def crear_calificacion(self, articulo_id: str, pasajero_id: str | None, util: str, fecha_iso: str) -> dict:
        data = {"articulo_id": articulo_id, "util": util, "fecha": fecha_iso}
        if pasajero_id:
            data["pasajero_id"] = pasajero_id
        return await self._client.create_record("articulo_calificaciones", data)

    async def calificaciones_de_articulo(self, articulo_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "articulo_calificaciones", {"filter": f'articulo_id="{articulo_id}"', "perPage": 500}
        )
        return resultado["items"]

    async def todas_las_calificaciones(self) -> list[dict]:
        resultado = await self._client.list_records("articulo_calificaciones", {"perPage": 2000})
        return resultado["items"]

    # ── casos_escalados ───────────────────────────────────────────────
    async def crear_caso(self, data: dict) -> dict:
        return await self._client.create_record("casos_escalados", data)

    async def listar_casos(self, estado: str | None = None) -> list[dict]:
        params = {"sort": "-fecha_creacion", "perPage": 200}
        if estado:
            params["filter"] = f'estado="{estado}"'
        resultado = await self._client.list_records("casos_escalados", params)
        return resultado["items"]

    async def obtener_caso(self, caso_id: str) -> dict | None:
        try:
            return await self._client.get_record("casos_escalados", caso_id)
        except PocketBaseError:
            return None

    async def actualizar_caso(self, caso_id: str, data: dict) -> dict:
        return await self._client.update_record("casos_escalados", caso_id, data)

    async def casos_en_periodo(self, desde_iso: str) -> list[dict]:
        resultado = await self._client.list_records(
            "casos_escalados", {"filter": f'fecha_creacion>="{desde_iso}"', "perPage": 2000}
        )
        return resultado["items"]
