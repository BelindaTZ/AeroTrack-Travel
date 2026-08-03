"""`disrupciones`, `notificaciones` son OPERACIONAL — migradas a MinIO
junto con `reservas` (paso 5 del plan; `notificaciones.reserva_id` es
`required=true`, confirmado en el barrido de relation fields de la
sesión — no se puede migrar por separado)."""

import datetime

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseClient, get_pocketbase_client

ENTIDAD_DISRUPCIONES = "disrupciones"
ENTIDAD_NOTIFICACIONES = "notificaciones"


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


def _crear_registro(data: dict) -> tuple[str, dict]:
    id_ = moc.generar_id()
    return id_, {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}


class DisrupcionesRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── disrupciones ─────────────────────────────────────────────────
    async def crear_disrupcion(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_DISRUPCIONES, id_, registro)

    async def obtener_disrupcion(self, disrupcion_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_DISRUPCIONES, disrupcion_id)

    async def disrupciones_de_vuelo_y_tipo(self, vuelo_id: str, tipo_cambio: str) -> list[dict]:
        disrupciones = await moc.listar_todos(ENTIDAD_DISRUPCIONES)
        return [
            d for d in disrupciones
            if d.get("vuelo_id") == vuelo_id and d.get("tipo_cambio") == tipo_cambio and d.get("estado") == "activa"
        ]

    async def actualizar_disrupcion(self, disrupcion_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_DISRUPCIONES, disrupcion_id, _mutar)

    async def listar_disrupciones(
        self, estado: str | None = None, tipo_cambio: str | None = None
    ) -> list[dict]:
        """WP-12 (auditoría de WorkPanels, 2026-07-31) — antes solo se leía
        por vuelo+tipo desde los servicios automáticos; sin listado general
        no había forma de revisar disrupciones desde el backoffice."""
        disrupciones = await moc.listar_todos(ENTIDAD_DISRUPCIONES)
        if estado:
            disrupciones = [d for d in disrupciones if d.get("estado") == estado]
        if tipo_cambio:
            disrupciones = [d for d in disrupciones if d.get("tipo_cambio") == tipo_cambio]
        disrupciones.sort(key=lambda d: d.get("fecha_deteccion") or "", reverse=True)
        return disrupciones

    # ── notificaciones ───────────────────────────────────────────────
    async def crear_notificacion(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_NOTIFICACIONES, id_, registro)

    async def obtener_notificacion(self, notificacion_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_NOTIFICACIONES, notificacion_id)

    async def actualizar_notificacion(self, notificacion_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_NOTIFICACIONES, notificacion_id, _mutar)

    async def notificaciones_de_disrupcion_y_pasajero(
        self, disrupcion_id: str, pasajero_id: str
    ) -> list[dict]:
        notificaciones = await moc.listar_todos(ENTIDAD_NOTIFICACIONES)
        return [
            n for n in notificaciones
            if n.get("disrupcion_id") == disrupcion_id and n.get("pasajero_id") == pasajero_id
        ]

    async def notificaciones_de_pasajero(
        self,
        pasajero_id: str,
        canal: str | None = None,
        estado_envio: str | None = None,
    ) -> list[dict]:
        notificaciones = await moc.listar_todos(ENTIDAD_NOTIFICACIONES)
        resultado = [n for n in notificaciones if n.get("pasajero_id") == pasajero_id]
        if canal:
            resultado = [n for n in resultado if n.get("canal") == canal]
        if estado_envio:
            resultado = [n for n in resultado if n.get("estado_envio") == estado_envio]
        resultado.sort(key=lambda n: n.get("created") or "", reverse=True)
        return resultado

    async def notificaciones_fallidas(self) -> list[dict]:
        notificaciones = await moc.listar_todos(ENTIDAD_NOTIFICACIONES)
        resultado = [n for n in notificaciones if n.get("estado_envio") == "fallido"]
        resultado.sort(key=lambda n: n.get("created") or "", reverse=True)
        return resultado

    async def listar_notificaciones(
        self, filtro_campos: dict | None = None, desde: str | None = None, hasta: str | None = None
    ) -> list[dict]:
        """`filtro_campos`: dict de igualdad exacta campo->valor (reemplaza
        el string-filter de PocketBase, ver `FacturacionRepository.listar_comisiones`).
        `desde`/`hasta` filtran por `created` (fecha en que se generó la
        notificación, no `fecha_envio` — esta puede quedar vacía si el envío
        todavía está `pendiente`/`fallido`, ver IS-12)."""
        notificaciones = await moc.listar_todos(ENTIDAD_NOTIFICACIONES)
        if filtro_campos:
            notificaciones = [
                n for n in notificaciones
                if all(n.get(campo) == valor for campo, valor in filtro_campos.items())
            ]
        if desde:
            notificaciones = [n for n in notificaciones if (n.get("created") or "") >= desde]
        if hasta:
            notificaciones = [n for n in notificaciones if (n.get("created") or "") <= hasta]
        notificaciones.sort(key=lambda n: n.get("created") or "", reverse=True)
        return notificaciones

    # ── configuración ────────────────────────────────────────────────
    async def config(self, clave: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        return await self._client.get_first("configuracion_sistema", f'clave="{safe}"')

    async def actualizar_config(self, clave: str, valor: str) -> dict:
        registro = await self.config(clave)
        if registro is None:
            raise RuntimeError(f"configuracion_sistema.{clave} no está sembrado")
        return await self._client.update_record("configuracion_sistema", registro["id"], {"valor": valor})
