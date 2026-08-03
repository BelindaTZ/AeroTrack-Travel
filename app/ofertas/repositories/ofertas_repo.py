"""Consultas de Ofertas y Promociones sobre `ofertas_destacadas`,
`cupones_descuento`, `newsletter_suscripciones`, `campanas_email` en
PocketBase (CONFIG/contenido admin-managed). `busquedas_recientes`
(propiedad de Cuenta) y `cupones_uso`/`reserva_items` (propiedad de
Reservas) son OPERACIONAL y ya viven en MinIO — ver plan de migración.
`cupones_uso` migró junto con `reservas` (paso 5, `reserva_id` es
`required=true`, confirmado en el barrido de relation fields)."""

import datetime

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


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

    async def listar_ofertas_admin(
        self, tipo_producto: str | None = None, estado: str | None = None
    ) -> list[dict]:
        condiciones = []
        if tipo_producto:
            condiciones.append(f'tipo_producto="{tipo_producto}"')
        if estado == "activo":
            condiciones.append("activa=true")
        elif estado == "inactivo":
            condiciones.append("activa=false")
        params: dict = {"sort": "-fecha_inicio", "perPage": 200}
        if condiciones:
            params["filter"] = " && ".join(condiciones)
        resultado = await self._client.list_records("ofertas_destacadas", params)
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

    async def listar_cupones(
        self, codigo: str | None = None, tipo: str | None = None, estado: str | None = None
    ) -> list[dict]:
        condiciones = []
        if codigo:
            safe = codigo.replace('"', '\\"')
            condiciones.append(f'codigo~"{safe}"')
        if tipo:
            condiciones.append(f'tipo="{tipo}"')
        if estado == "activo":
            condiciones.append("activo=true")
        elif estado == "inactivo":
            condiciones.append("activo=false")
        params: dict = {"sort": "-created", "perPage": 200}
        if condiciones:
            params["filter"] = " && ".join(condiciones)
        resultado = await self._client.list_records("cupones_descuento", params)
        return resultado["items"]

    async def crear_cupon(self, data: dict) -> dict:
        return await self._client.create_record("cupones_descuento", data)

    async def actualizar_cupon(self, cupon_id: str, data: dict) -> dict:
        return await self._client.update_record("cupones_descuento", cupon_id, data)

    # ── cupones_uso (OPERACIONAL, MinIO) ─────────────────────────────
    async def uso_existente(self, cupon_id: str, reserva_id: str) -> dict | None:
        usos = await moc.listar_todos("cupones_uso")
        return next(
            (u for u in usos if u.get("cupon_id") == cupon_id and u.get("reserva_id") == reserva_id), None
        )

    async def registrar_uso(self, cupon_id: str, reserva_id: str, monto_descontado: float, fecha_iso: str) -> dict:
        id_ = moc.generar_id()
        registro = {
            "id": id_, "created": _timestamp(), "updated": _timestamp(),
            "cupon_id": cupon_id, "reserva_id": reserva_id,
            "monto_descontado": monto_descontado, "fecha_uso": fecha_iso,
        }
        return await moc.crear("cupones_uso", id_, registro)

    async def usos_en_periodo(self, desde_iso: str) -> list[dict]:
        usos = await moc.listar_todos("cupones_uso")
        return [u for u in usos if (u.get("fecha_uso") or "") >= desde_iso]

    # ── busquedas_recientes (lectura, propiedad de Cuenta/Mis Viajes —
    #    ver RN-CTA-001; este módulo solo lee para agregar CU-O102).
    #    OPERACIONAL, migrada a MinIO — ver plan de migración. ─────────
    async def busquedas_vuelo_de_pasajero(self, pasajero_id: str, limite: int = 20) -> list[dict]:
        busquedas = await moc.listar_todos("busquedas_recientes")
        resultado = [
            b for b in busquedas
            if b.get("pasajero_id") == pasajero_id and b.get("tipo_producto") == "vuelo"
        ]
        resultado.sort(key=lambda b: b.get("fecha") or "", reverse=True)
        return resultado[:limite]

    async def todas_las_busquedas_de_vuelo(self, limite: int = 500) -> list[dict]:
        busquedas = await moc.listar_todos("busquedas_recientes")
        resultado = [b for b in busquedas if b.get("tipo_producto") == "vuelo"]
        return resultado[:limite]

    # ── reserva_items (lectura, propiedad de Reservas — para pesar
    #    destinos populares con reservas reales, no solo búsquedas).
    #    OPERACIONAL, MinIO — ver plan de migración. ───────────────────
    async def reserva_items_de_vuelo(self, limite: int = 1000) -> list[dict]:
        items = await moc.listar_todos("reserva_items")
        return [i for i in items if i.get("tipo_producto") == "vuelo"][:limite]

    # ── newsletter_suscripciones (OPERACIONAL, MinIO) ────────────────
    # Última de las 15 colecciones con relation a `pasajeros` en migrar —
    # ver espejo RC-OP-003 en `PasajerosRepository`, ya se puede quitar.
    async def suscripcion_existente(self, email: str) -> dict | None:
        suscripciones = await moc.listar_todos("newsletter_suscripciones")
        return next((s for s in suscripciones if s.get("email") == email), None)

    async def crear_suscripcion(self, data: dict) -> dict:
        id_ = moc.generar_id()
        # `pasajero_id` siempre presente (aunque vacío) — un registro en
        # MinIO es sparse, a diferencia de PocketBase que siempre trae el
        # esquema completo; ver mismo fix en `ReservasRepository.agregar_pasajero`.
        registro = {
            "id": id_, "created": _timestamp(), "updated": _timestamp(), "pasajero_id": "", **data,
        }
        return await moc.crear("newsletter_suscripciones", id_, registro)

    async def reactivar_suscripcion(self, suscripcion_id: str) -> dict:
        def _mutar(actual: dict) -> dict:
            actual["activo"] = True
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento("newsletter_suscripciones", suscripcion_id, _mutar)

    async def desactivar_suscripcion(self, suscripcion_id: str) -> dict:
        def _mutar(actual: dict) -> dict:
            actual["activo"] = False
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento("newsletter_suscripciones", suscripcion_id, _mutar)

    async def obtener_suscripcion(self, suscripcion_id: str) -> dict | None:
        suscripciones = await moc.listar_todos("newsletter_suscripciones")
        return next((s for s in suscripciones if s.get("id") == suscripcion_id), None)

    async def listar_suscriptores_activos(self) -> list[dict]:
        suscripciones = await moc.listar_todos("newsletter_suscripciones")
        return [s for s in suscripciones if s.get("activo")]

    async def listar_todos_suscriptores(
        self, email: str | None = None, estado: str | None = None
    ) -> list[dict]:
        suscripciones = await moc.listar_todos("newsletter_suscripciones")
        if email:
            email_lower = email.lower()
            suscripciones = [s for s in suscripciones if email_lower in (s.get("email") or "").lower()]
        if estado == "activo":
            suscripciones = [s for s in suscripciones if s.get("activo")]
        elif estado == "inactivo":
            suscripciones = [s for s in suscripciones if not s.get("activo")]
        suscripciones.sort(key=lambda s: s.get("fecha_suscripcion") or "", reverse=True)
        return suscripciones

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
