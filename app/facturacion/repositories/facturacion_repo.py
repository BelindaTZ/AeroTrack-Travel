"""Consultas de Facturación sobre `pagos`, `metodos_pago`, `comisiones`,
`remesas`, `remesa_comisiones`, `reembolsos`, `facturas` en PocketBase."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class FacturacionRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── pagos ────────────────────────────────────────────────────────
    async def crear_pago(self, data: dict) -> dict:
        return await self._client.create_record("pagos", data)

    async def actualizar_pago(self, pago_id: str, data: dict) -> dict:
        return await self._client.update_record("pagos", pago_id, data)

    async def pago_exitoso_de_reserva(self, reserva_id: str) -> dict | None:
        return await self._client.get_first(
            "pagos", f'reserva_id="{reserva_id}" && estado="exitoso"'
        )

    async def pagos_de_reserva(self, reserva_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "pagos", {"filter": f'reserva_id="{reserva_id}"', "sort": "-created", "perPage": 50}
        )
        return resultado["items"]

    async def obtener_pago(self, pago_id: str) -> dict | None:
        try:
            return await self._client.get_record("pagos", pago_id)
        except PocketBaseError:
            return None

    async def metodo_pago_por_defecto(self) -> dict:
        metodo = await self._client.get_first("metodos_pago", 'activo=true')
        if metodo is None:
            raise RuntimeError("No hay ningún metodos_pago activo sembrado")
        return metodo

    # ── facturas ─────────────────────────────────────────────────────
    async def crear_factura(self, data: dict) -> dict:
        return await self._client.create_record("facturas", data)

    async def obtener_factura(self, factura_id: str) -> dict | None:
        try:
            return await self._client.get_record("facturas", factura_id)
        except PocketBaseError:
            return None

    async def factura_de_pago(self, pago_id: str) -> dict | None:
        return await self._client.get_first("facturas", f'pago_id="{pago_id}"')

    # ── comisiones ───────────────────────────────────────────────────
    async def crear_comision(self, data: dict) -> dict:
        return await self._client.create_record("comisiones", data)

    async def obtener_comision(self, comision_id: str) -> dict | None:
        try:
            return await self._client.get_record("comisiones", comision_id)
        except PocketBaseError:
            return None

    async def actualizar_comision(self, comision_id: str, data: dict) -> dict:
        return await self._client.update_record("comisiones", comision_id, data)

    async def listar_comisiones(self, filtro: str | None = None) -> list[dict]:
        params = {"perPage": 200, "sort": "-created"}
        if filtro:
            params["filter"] = filtro
        resultado = await self._client.list_records("comisiones", params)
        return resultado["items"]

    async def comisiones_cobradas_sin_remesa(self, aerolinea_id: str) -> list[dict]:
        todas = await self.listar_comisiones(f'aerolinea_id="{aerolinea_id}" && estado="cobrada"')
        ya_remesadas = await self._client.list_records(
            "remesa_comisiones", {"perPage": 500}
        )
        ids_remesados = {rc["comision_id"] for rc in ya_remesadas["items"]}
        return [c for c in todas if c["id"] not in ids_remesados]

    # ── remesas ──────────────────────────────────────────────────────
    async def crear_remesa(self, data: dict) -> dict:
        return await self._client.create_record("remesas", data)

    async def agregar_remesa_comision(self, remesa_id: str, comision_id: str) -> dict:
        return await self._client.create_record(
            "remesa_comisiones", {"remesa_id": remesa_id, "comision_id": comision_id}
        )

    async def listar_remesas(self) -> list[dict]:
        resultado = await self._client.list_records("remesas", {"perPage": 100, "sort": "-created"})
        return resultado["items"]

    # ── reembolsos ───────────────────────────────────────────────────
    async def crear_reembolso(self, data: dict) -> dict:
        return await self._client.create_record("reembolsos", data)

    async def actualizar_reembolso(self, reembolso_id: str, data: dict) -> dict:
        return await self._client.update_record("reembolsos", reembolso_id, data)

    # ── configuración ────────────────────────────────────────────────
    async def config(self, clave: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        return await self._client.get_first("configuracion_sistema", f'clave="{safe}"')
