"""`reservas`, `reserva_items`, `reserva_pasajeros`, `reserva_extras`,
`alertas_precio` son OPERACIONAL — migradas a MinIO (paso 5 del plan,
junto con facturación/disrupciones/cupones_uso por las relations
cruzadas). Es el módulo más acoplado del sistema — 9+ módulos importan
`ReservasRepository`.

Lee `pasajeros` (propiedad de Pasajeros, ya en MinIO) y `usuarios`
(propiedad de Seguridad, sigue en PocketBase) pero nunca escribe ahí —
este módulo solo resuelve el titular ya existente, no crea perfiles de
pasajero (ver nota de alcance en `plan.md`).

`reserva_pasajeros.asiento_id -> asientos_vuelo`: caso mixto sin resolver
(mapa de asientos sigue STAGING en PocketBase, la asignación en sí queda
aquí como antes — no se tocó en esta fase, ver plan de migración).
"""

import datetime

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client

ENTIDAD_RESERVAS = "reservas"
ENTIDAD_ITEMS = "reserva_items"
ENTIDAD_PASAJEROS_RESERVA = "reserva_pasajeros"
ENTIDAD_EXTRAS = "reserva_extras"
ENTIDAD_ALERTAS = "alertas_precio"


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


def _crear_registro(data: dict) -> tuple[str, dict]:
    id_ = moc.generar_id()
    return id_, {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}


class ReservasRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()
        self._pasajeros = PasajerosRepository(self._client)

    # ── pasajeros (lectura, MinIO — ver PasajerosRepository) ────────────
    async def pasajero_de_usuario(self, usuario_id: str) -> dict | None:
        return await self._pasajeros.pasajero_de_usuario(usuario_id)

    async def pasajero_por_email(self, email: str) -> dict | None:
        safe = email.replace('"', '\\"')
        usuario = await self._client.get_first("usuarios", f'email="{safe}"')
        if usuario is None:
            return None
        return await self.pasajero_de_usuario(usuario["id"])

    async def obtener_pasajero(self, pasajero_id: str) -> dict | None:
        return await self._pasajeros.obtener_pasajero(pasajero_id)

    async def nombre_de_pasajero(self, pasajero_id: str) -> str:
        pasajero = await self.obtener_pasajero(pasajero_id)
        if pasajero is None:
            return "—"
        try:
            usuario = await self._client.get_record("usuarios", pasajero["usuario_id"])
        except PocketBaseError:
            return "—"
        return usuario.get("nombre_completo") or usuario.get("email") or "—"

    # ── reservas ─────────────────────────────────────────────────────
    async def crear_reserva(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_RESERVAS, id_, registro)

    async def obtener_reserva(self, reserva_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_RESERVAS, reserva_id)

    async def actualizar_reserva(self, reserva_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_RESERVAS, reserva_id, _mutar)

    async def guardar_voucher(self, reserva_id: str, filename: str, contenido: bytes) -> dict:
        """El voucher PDF se guarda como objeto binario propio en el bucket
        operacional (no como campo `file` de PocketBase, que ya no aplica
        acá) — clave predecible por reserva_id, sobreescribe en cada
        regeneración."""
        await moc.subir_archivo("reservas_vouchers", reserva_id, filename, contenido, "application/pdf")
        return await self.actualizar_reserva(reserva_id, {"voucher_pdf": filename})

    async def descargar_voucher(self, reserva_id: str, filename: str) -> bytes:
        return await moc.descargar_archivo("reservas_vouchers", reserva_id, filename)

    async def obtener_por_codigo(self, codigo_reserva: str) -> dict | None:
        reservas = await moc.listar_todos(ENTIDAD_RESERVAS)
        return next((r for r in reservas if r.get("codigo_reserva") == codigo_reserva), None)

    async def listar_reservas_de_pasajero(self, pasajero_id: str) -> list[dict]:
        reservas = await moc.listar_todos(ENTIDAD_RESERVAS)
        resultado = [r for r in reservas if r.get("pasajero_titular_id") == pasajero_id]
        resultado.sort(key=lambda r: r.get("fecha_reserva") or "", reverse=True)
        return resultado

    async def listar_reservas_confirmadas_de_vuelo(self, vuelo_id: str) -> list[dict]:
        """Reservas afectadas por una disrupción — Disrupciones necesita
        saber a quién notificar cuando un vuelo cambia."""
        reservas = await moc.listar_todos(ENTIDAD_RESERVAS)
        return [
            r for r in reservas
            if r.get("vuelo_id") == vuelo_id and r.get("estado") in ("confirmada", "modificada")
        ]

    async def listar_pendientes_vencidas(self, ahora_iso: str) -> list[dict]:
        reservas = await moc.listar_todos(ENTIDAD_RESERVAS)
        return [
            r for r in reservas
            if r.get("estado") == "pendiente_pago" and (r.get("fecha_expiracion_pago") or "") <= ahora_iso
        ]

    async def listar_todas(
        self,
        estado: str | None = None,
        desde: str | None = None,
        hasta: str | None = None,
        agente_id: str | None = None,
    ) -> list[dict]:
        """CU-T16/T17/T43/T44 — reporte general de reservas, filtrable por
        estado/período/agente. Filtrado en memoria (mismo criterio que
        `listar_pendientes_vencidas`) — el volumen de reservas de este
        proyecto no justifica una consulta MinIO más elaborada."""
        reservas = await moc.listar_todos(ENTIDAD_RESERVAS)
        resultado = reservas
        if estado:
            resultado = [r for r in resultado if r.get("estado") == estado]
        if desde:
            resultado = [r for r in resultado if (r.get("fecha_reserva") or "") >= desde]
        if hasta:
            resultado = [r for r in resultado if (r.get("fecha_reserva") or "") <= hasta]
        if agente_id:
            resultado = [r for r in resultado if r.get("agente_id") == agente_id]
        resultado.sort(key=lambda r: r.get("fecha_reserva") or "", reverse=True)
        return resultado

    # ── reserva_items (rediseño v3, dueño: este módulo) ─────────────────
    # NOTA: el flujo actual (solo Vuelos) sigue escribiendo también
    # reservas.vuelo_id/tarifa_id (dual-write) — reserva_items se agrega en
    # paralelo para que Paquetes/Carrito/Cuenta-Mis-Viajes tengan de dónde
    # leer sin depender de un único vuelo_id/tarifa_id en la cabecera, que
    # deja de tener sentido para una reserva multi-producto. Ver
    # specs/000-sistema-general/pendientes-implementacion-codigo.md.
    async def crear_item(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_ITEMS, id_, registro)

    async def items_de_reserva(self, reserva_id: str) -> list[dict]:
        items = await moc.listar_todos(ENTIDAD_ITEMS)
        return [i for i in items if i.get("reserva_id") == reserva_id]

    async def listar_todos_items(
        self, tipo_producto: str | None = None, desde: str | None = None, hasta: str | None = None
    ) -> list[dict]:
        """IS-10 (auditoría de informes simples, sesión 2026-08-01) —
        listado general de `reserva_items` sin acotar a una reserva, para
        el informe "ítems por tipo de producto". `desde`/`hasta` filtran
        por `created` del ítem (cuándo se agregó a la reserva)."""
        items = await moc.listar_todos(ENTIDAD_ITEMS)
        if tipo_producto:
            items = [i for i in items if i.get("tipo_producto") == tipo_producto]
        if desde:
            items = [i for i in items if (i.get("created") or "") >= desde]
        if hasta:
            items = [i for i in items if (i.get("created") or "") <= hasta]
        items.sort(key=lambda i: i.get("created") or "", reverse=True)
        return items

    async def item_de_reserva_por_tipo(self, reserva_id: str, tipo_producto: str) -> dict | None:
        items = await self.items_de_reserva(reserva_id)
        return next((i for i in items if i.get("tipo_producto") == tipo_producto), None)

    async def actualizar_item(self, item_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_ITEMS, item_id, _mutar)

    # ── reserva_pasajeros ────────────────────────────────────────────
    async def agregar_pasajero(
        self,
        reserva_id: str,
        pasajero_id: str,
        tipo_pasajero: str = "adulto",
        asiento_id: str | None = None,
    ) -> dict:
        # `asiento_id`/`asiento_asignado_por` siempre presentes (aunque
        # vacíos) — a diferencia de PocketBase, un registro en MinIO es
        # sparse (solo trae lo que se escribió), y código como
        # `asientos_service.py` hace `dict["asiento_id"]` esperando que el
        # campo siempre exista (aunque sea "").
        data = {
            "reserva_id": reserva_id, "pasajero_id": pasajero_id, "tipo_pasajero": tipo_pasajero,
            "asiento_id": "", "asiento_asignado_por": "",
        }
        if asiento_id:
            data["asiento_id"] = asiento_id
            data["asiento_asignado_por"] = "pasajero"
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_PASAJEROS_RESERVA, id_, registro)

    async def pasajeros_de_reserva(self, reserva_id: str) -> list[dict]:
        pasajeros = await moc.listar_todos(ENTIDAD_PASAJEROS_RESERVA)
        return [p for p in pasajeros if p.get("reserva_id") == reserva_id]

    async def actualizar_pasajero(self, reserva_pasajero_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_PASAJEROS_RESERVA, reserva_pasajero_id, _mutar)

    async def pasajeros_sin_asiento(self) -> list[dict]:
        """RF-VUE-013 — candidatos a asignación automática: sin importar el
        vuelo, se filtra por ventana de check-in del lado del servicio (no
        hay forma de expresar esa comparación acá, que no conoce
        `vuelos_catalogo.fecha_salida` desde esta colección)."""
        pasajeros = await moc.listar_todos(ENTIDAD_PASAJEROS_RESERVA)
        return [p for p in pasajeros if not p.get("asiento_id")]

    # ── reserva_extras ───────────────────────────────────────────────
    async def agregar_extra(self, reserva_id: str, tipo: str, descripcion: str, precio: float) -> dict:
        id_, registro = _crear_registro(
            {"reserva_id": reserva_id, "tipo": tipo, "descripcion": descripcion, "precio": precio}
        )
        return await moc.crear(ENTIDAD_EXTRAS, id_, registro)

    async def extras_de_reserva(self, reserva_id: str) -> list[dict]:
        extras = await moc.listar_todos(ENTIDAD_EXTRAS)
        return [e for e in extras if e.get("reserva_id") == reserva_id]

    async def eliminar_extras_de_reserva(self, reserva_id: str) -> None:
        for extra in await self.extras_de_reserva(reserva_id):
            await moc.eliminar(ENTIDAD_EXTRAS, extra["id"])

    # ── alertas_precio ───────────────────────────────────────────────
    async def crear_alerta(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_ALERTAS, id_, registro)

    async def listar_alertas_de_pasajero(self, pasajero_id: str) -> list[dict]:
        alertas = await moc.listar_todos(ENTIDAD_ALERTAS)
        return [a for a in alertas if a.get("pasajero_id") == pasajero_id]

    async def listar_todas_alertas(self) -> list[dict]:
        """ETL clientes (Fase B, sesión 2026-08-02) — todas las alertas sin
        acotar a un pasajero, para agg_alertas_conversion."""
        return await moc.listar_todos(ENTIDAD_ALERTAS)

    # ── configuración ────────────────────────────────────────────────
    async def config(self, clave: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        return await self._client.get_first("configuracion_sistema", f'clave="{safe}"')
