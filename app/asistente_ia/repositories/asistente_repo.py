"""`conversaciones_ia`, `mensajes_ia` son OPERACIONAL — migradas a MinIO
(ver plan de migración). `pasajero_id` es requerido en el esquema real
(dbml v3, confirmado — no es un drift) — una conversación anónima nunca se
persiste, ver `contexto_service`/`asistente_service`. Migran como par
(`mensajes_ia.conversacion_id` depende de `conversaciones_ia`, confirmado
en el barrido de relation fields de la sesión). `configuracion_sistema` es
CONFIG y sigue en PocketBase."""

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseClient, get_pocketbase_client

ENTIDAD_CONVERSACIONES = "conversaciones_ia"
ENTIDAD_MENSAJES = "mensajes_ia"


class AsistenteRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── conversaciones_ia ─────────────────────────────────────────────
    async def crear_conversacion(self, pasajero_id: str, fecha_iso: str) -> dict:
        id_ = moc.generar_id()
        registro = {
            "id": id_, "created": fecha_iso, "updated": fecha_iso,
            "pasajero_id": pasajero_id, "fecha_inicio": fecha_iso,
            "fecha_ultima_actividad": fecha_iso, "activa": True,
        }
        return await moc.crear(ENTIDAD_CONVERSACIONES, id_, registro)

    async def obtener_conversacion(self, conversacion_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_CONVERSACIONES, conversacion_id)

    async def conversacion_activa_de_pasajero(self, pasajero_id: str) -> dict | None:
        conversaciones = await moc.listar_todos(ENTIDAD_CONVERSACIONES)
        return next(
            (c for c in conversaciones if c.get("pasajero_id") == pasajero_id and c.get("activa")), None
        )

    async def listar_conversaciones_de_pasajero(self, pasajero_id: str) -> list[dict]:
        conversaciones = await moc.listar_todos(ENTIDAD_CONVERSACIONES)
        resultado = [c for c in conversaciones if c.get("pasajero_id") == pasajero_id]
        resultado.sort(key=lambda c: c.get("fecha_ultima_actividad") or "", reverse=True)
        return resultado

    async def cerrar_conversacion(self, conversacion_id: str) -> None:
        def _mutar(actual: dict) -> dict:
            actual["activa"] = False
            return actual

        await moc.actualizar_con_reintento(ENTIDAD_CONVERSACIONES, conversacion_id, _mutar)

    async def actualizar_actividad(self, conversacion_id: str, fecha_iso: str, titulo: str | None = None) -> None:
        def _mutar(actual: dict) -> dict:
            actual["fecha_ultima_actividad"] = fecha_iso
            if titulo:
                actual["titulo"] = titulo
            return actual

        await moc.actualizar_con_reintento(ENTIDAD_CONVERSACIONES, conversacion_id, _mutar)

    # ── mensajes_ia ───────────────────────────────────────────────────
    async def crear_mensaje(self, conversacion_id: str, rol: str, contenido: str, fecha_iso: str) -> dict:
        id_ = moc.generar_id()
        registro = {
            "id": id_, "created": fecha_iso, "updated": fecha_iso,
            "conversacion_id": conversacion_id, "rol": rol, "contenido": contenido, "fecha": fecha_iso,
        }
        return await moc.crear(ENTIDAD_MENSAJES, id_, registro)

    async def mensajes_de_conversacion(self, conversacion_id: str) -> list[dict]:
        mensajes = await moc.listar_todos(ENTIDAD_MENSAJES)
        resultado = [m for m in mensajes if m.get("conversacion_id") == conversacion_id]
        resultado.sort(key=lambda m: m.get("fecha") or "")
        return resultado

    async def obtener_mensaje(self, mensaje_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_MENSAJES, mensaje_id)

    async def calificar_mensaje(self, mensaje_id: str, calificacion: str) -> dict:
        def _mutar(actual: dict) -> dict:
            actual["calificacion"] = calificacion
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_MENSAJES, mensaje_id, _mutar)

    async def listar_todos_mensajes(self) -> list[dict]:
        """ETL operaciones (Fase B, sesión 2026-08-02) — todos los mensajes
        sin acotar a una conversación."""
        return await moc.listar_todos(ENTIDAD_MENSAJES)

    async def listar_todas_conversaciones(self) -> list[dict]:
        return await moc.listar_todos(ENTIDAD_CONVERSACIONES)

    async def mensajes_de_pasajero_en_periodo(self, desde_iso: str, limite: int = 2000) -> list[dict]:
        """Para el reporte CU-T33 — todos los mensajes de rol `usuario` en
        el período, sin filtrar por pasajero (vista agregada de Admin)."""
        conversaciones = await moc.listar_todos(ENTIDAD_CONVERSACIONES)
        ids = {c["id"] for c in conversaciones if (c.get("fecha_ultima_actividad") or "") >= desde_iso}
        mensajes = await moc.listar_todos(ENTIDAD_MENSAJES)
        return [m for m in mensajes if m.get("conversacion_id") in ids][:limite]

    # ── configuración (CU-T34, CONFIG — sigue en PocketBase) ─────────
    async def config(self, clave: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        return await self._client.get_first("configuracion_sistema", f'clave="{safe}"')

    async def actualizar_config(self, clave: str, valor: str, modificado_por: str) -> dict:
        registro = await self.config(clave)
        if registro is None:
            return await self._client.create_record(
                "configuracion_sistema",
                {"clave": clave, "valor": valor, "categoria": "asistente_ia", "modificado_por": modificado_por},
            )
        return await self._client.update_record(
            "configuracion_sistema", registro["id"], {"valor": valor, "modificado_por": modificado_por}
        )
