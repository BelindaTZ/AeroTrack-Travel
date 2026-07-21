"""Consultas de Integraciones sobre `fuentes_datos_externas` y
`sincronizaciones_log` en PocketBase."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class IntegracionesRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── fuentes_datos_externas ──────────────────────────────────────────
    async def listar_fuentes(self) -> list[dict]:
        resultado = await self._client.list_records(
            "fuentes_datos_externas", {"perPage": 200, "sort": "nombre"}
        )
        return resultado["items"]

    async def obtener_fuente(self, fuente_id: str) -> dict | None:
        try:
            return await self._client.get_record("fuentes_datos_externas", fuente_id)
        except PocketBaseError:
            return None

    async def actualizar_fuente(self, fuente_id: str, data: dict) -> dict:
        return await self._client.update_record("fuentes_datos_externas", fuente_id, data)

    # ── sincronizaciones_log ────────────────────────────────────────────
    async def crear_log(self, data: dict) -> dict:
        return await self._client.create_record("sincronizaciones_log", data)

    async def listar_bitacora(self, filtro: str | None = None) -> list[dict]:
        params = {"perPage": 200, "sort": "-fecha_inicio"}
        if filtro:
            params["filter"] = filtro
        resultado = await self._client.list_records("sincronizaciones_log", params)
        return resultado["items"]

    async def cuota_consumida_por_fuente(self, fuente_id: str) -> int:
        resultado = await self._client.list_records(
            "sincronizaciones_log",
            {"filter": f'fuente_id="{fuente_id}"', "perPage": 500},
        )
        return sum(item.get("unidades_cuota_consumidas") or 0 for item in resultado["items"])
