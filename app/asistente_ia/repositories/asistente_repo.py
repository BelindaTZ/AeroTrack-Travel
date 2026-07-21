"""Consultas de Asistente IA sobre `conversaciones_ia`, `mensajes_ia` en
PocketBase. `pasajero_id` es requerido en el esquema real (dbml v3,
confirmado — no es un drift) — una conversación anónima nunca se
persiste, ver `contexto_service`/`asistente_service`."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class AsistenteRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── conversaciones_ia ─────────────────────────────────────────────
    async def crear_conversacion(self, pasajero_id: str, fecha_iso: str) -> dict:
        return await self._client.create_record(
            "conversaciones_ia",
            {"pasajero_id": pasajero_id, "fecha_inicio": fecha_iso, "fecha_ultima_actividad": fecha_iso, "activa": True},
        )

    async def obtener_conversacion(self, conversacion_id: str) -> dict | None:
        try:
            return await self._client.get_record("conversaciones_ia", conversacion_id)
        except PocketBaseError:
            return None

    async def conversacion_activa_de_pasajero(self, pasajero_id: str) -> dict | None:
        return await self._client.get_first(
            "conversaciones_ia", f'pasajero_id="{pasajero_id}" && activa=true'
        )

    async def listar_conversaciones_de_pasajero(self, pasajero_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "conversaciones_ia", {"filter": f'pasajero_id="{pasajero_id}"', "sort": "-fecha_ultima_actividad", "perPage": 100}
        )
        return resultado["items"]

    async def cerrar_conversacion(self, conversacion_id: str) -> None:
        await self._client.update_record("conversaciones_ia", conversacion_id, {"activa": False})

    async def actualizar_actividad(self, conversacion_id: str, fecha_iso: str, titulo: str | None = None) -> None:
        data = {"fecha_ultima_actividad": fecha_iso}
        if titulo:
            data["titulo"] = titulo
        await self._client.update_record("conversaciones_ia", conversacion_id, data)

    # ── mensajes_ia ───────────────────────────────────────────────────
    async def crear_mensaje(self, conversacion_id: str, rol: str, contenido: str, fecha_iso: str) -> dict:
        return await self._client.create_record(
            "mensajes_ia", {"conversacion_id": conversacion_id, "rol": rol, "contenido": contenido, "fecha": fecha_iso}
        )

    async def mensajes_de_conversacion(self, conversacion_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "mensajes_ia", {"filter": f'conversacion_id="{conversacion_id}"', "sort": "fecha", "perPage": 200}
        )
        return resultado["items"]

    async def obtener_mensaje(self, mensaje_id: str) -> dict | None:
        try:
            return await self._client.get_record("mensajes_ia", mensaje_id)
        except PocketBaseError:
            return None

    async def calificar_mensaje(self, mensaje_id: str, calificacion: str) -> dict:
        return await self._client.update_record("mensajes_ia", mensaje_id, {"calificacion": calificacion})

    async def mensajes_de_pasajero_en_periodo(self, desde_iso: str, limite: int = 2000) -> list[dict]:
        """Para el reporte CU-T33 — todos los mensajes de rol `usuario` en
        el período, sin filtrar por pasajero (vista agregada de Admin)."""
        conversaciones = await self._client.list_records(
            "conversaciones_ia", {"filter": f'fecha_ultima_actividad>="{desde_iso}"', "perPage": limite}
        )
        ids = [c["id"] for c in conversaciones["items"]]
        mensajes: list[dict] = []
        for conv_id in ids:
            resultado = await self._client.list_records(
                "mensajes_ia", {"filter": f'conversacion_id="{conv_id}"', "sort": "fecha", "perPage": 200}
            )
            mensajes.extend(resultado["items"])
        return mensajes

    # ── configuración (CU-T34) ───────────────────────────────────────
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
