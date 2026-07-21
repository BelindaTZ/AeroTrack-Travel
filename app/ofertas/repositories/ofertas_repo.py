"""Consultas de Ofertas y Promociones sobre `ofertas_destacadas`,
`cupones_descuento`, `cupones_uso`, `newsletter_suscripciones`,
`campanas_email` en PocketBase."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class OfertasRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── ofertas_destacadas ───────────────────────────────────────────
    async def ofertas_vigentes(self, ahora_iso: str, tipo_producto: str | None = None) -> list[dict]:
        condiciones = ['activa=true', f'fecha_inicio<="{ahora_iso}"', f'fecha_fin>="{ahora_iso}"']
        if tipo_producto:
            condiciones.append(f'tipo_producto="{tipo_producto}"')
        resultado = await self._client.list_records(
            "ofertas_destacadas", {"filter": " && ".join(condiciones), "sort": "-fecha_inicio", "perPage": 100}
        )
        return resultado["items"]

    async def obtener_oferta(self, oferta_id: str) -> dict | None:
        try:
            return await self._client.get_record("ofertas_destacadas", oferta_id)
        except PocketBaseError:
            return None

    async def listar_ofertas_admin(self) -> list[dict]:
        resultado = await self._client.list_records("ofertas_destacadas", {"sort": "-fecha_inicio", "perPage": 200})
        return resultado["items"]

    async def crear_oferta(self, data: dict) -> dict:
        return await self._client.create_record("ofertas_destacadas", data)

    async def actualizar_oferta(self, oferta_id: str, data: dict) -> dict:
        return await self._client.update_record("ofertas_destacadas", oferta_id, data)

    # ── cupones_descuento ─────────────────────────────────────────────
    async def obtener_cupon_por_codigo(self, codigo: str) -> dict | None:
        safe = codigo.replace('"', '\\"')
        return await self._client.get_first("cupones_descuento", f'codigo="{safe}"')

    async def obtener_cupon(self, cupon_id: str) -> dict | None:
        try:
            return await self._client.get_record("cupones_descuento", cupon_id)
        except PocketBaseError:
            return None

    async def listar_cupones(self) -> list[dict]:
        resultado = await self._client.list_records("cupones_descuento", {"sort": "-created", "perPage": 200})
        return resultado["items"]

    async def crear_cupon(self, data: dict) -> dict:
        return await self._client.create_record("cupones_descuento", data)

    async def actualizar_cupon(self, cupon_id: str, data: dict) -> dict:
        return await self._client.update_record("cupones_descuento", cupon_id, data)

    # ── cupones_uso ───────────────────────────────────────────────────
    async def uso_existente(self, cupon_id: str, reserva_id: str) -> dict | None:
        return await self._client.get_first(
            "cupones_uso", f'cupon_id="{cupon_id}" && reserva_id="{reserva_id}"'
        )

    async def registrar_uso(self, cupon_id: str, reserva_id: str, monto_descontado: float, fecha_iso: str) -> dict:
        return await self._client.create_record(
            "cupones_uso",
            {"cupon_id": cupon_id, "reserva_id": reserva_id, "monto_descontado": monto_descontado, "fecha_uso": fecha_iso},
        )

    async def usos_en_periodo(self, desde_iso: str) -> list[dict]:
        resultado = await self._client.list_records(
            "cupones_uso", {"filter": f'fecha_uso>="{desde_iso}"', "perPage": 2000}
        )
        return resultado["items"]

    # ── busquedas_recientes (lectura, propiedad de Cuenta/Mis Viajes —
    #    ver RN-CTA-001; este módulo solo lee para agregar CU-O102) ────
    async def busquedas_vuelo_de_pasajero(self, pasajero_id: str, limite: int = 20) -> list[dict]:
        resultado = await self._client.list_records(
            "busquedas_recientes",
            {"filter": f'pasajero_id="{pasajero_id}" && tipo_producto="vuelo"', "sort": "-fecha", "perPage": limite},
        )
        return resultado["items"]

    async def todas_las_busquedas_de_vuelo(self, limite: int = 500) -> list[dict]:
        resultado = await self._client.list_records(
            "busquedas_recientes", {"filter": 'tipo_producto="vuelo"', "perPage": limite}
        )
        return resultado["items"]

    # ── reserva_items (lectura, propiedad de Reservas — para pesar
    #    destinos populares con reservas reales, no solo búsquedas) ────
    async def reserva_items_de_vuelo(self, limite: int = 1000) -> list[dict]:
        resultado = await self._client.list_records(
            "reserva_items", {"filter": 'tipo_producto="vuelo"', "perPage": limite}
        )
        return resultado["items"]

    # ── newsletter_suscripciones ─────────────────────────────────────
    async def suscripcion_existente(self, email: str) -> dict | None:
        safe = email.replace('"', '\\"')
        return await self._client.get_first("newsletter_suscripciones", f'email="{safe}"')

    async def crear_suscripcion(self, data: dict) -> dict:
        return await self._client.create_record("newsletter_suscripciones", data)

    async def listar_suscriptores_activos(self) -> list[dict]:
        resultado = await self._client.list_records(
            "newsletter_suscripciones", {"filter": "activo=true", "perPage": 2000}
        )
        return resultado["items"]

    # ── campanas_email ────────────────────────────────────────────────
    async def crear_campana(self, data: dict) -> dict:
        return await self._client.create_record("campanas_email", data)

    async def obtener_campana(self, campana_id: str) -> dict | None:
        try:
            return await self._client.get_record("campanas_email", campana_id)
        except PocketBaseError:
            return None

    async def listar_campanas(self) -> list[dict]:
        resultado = await self._client.list_records("campanas_email", {"sort": "-created", "perPage": 200})
        return resultado["items"]

    async def actualizar_campana(self, campana_id: str, data: dict) -> dict:
        return await self._client.update_record("campanas_email", campana_id, data)

    # ── configuración ────────────────────────────────────────────────
    async def config(self, clave: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        return await self._client.get_first("configuracion_sistema", f'clave="{safe}"')

    async def actualizar_config(self, clave: str, valor: str) -> dict:
        registro = await self.config(clave)
        return await self._client.update_record("configuracion_sistema", registro["id"], {"valor": valor})
