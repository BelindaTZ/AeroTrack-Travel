"""Consultas de Reservas sobre `reservas`, `reserva_pasajeros`,
`reserva_extras`, `alertas_precio` en PocketBase.

Lee `pasajeros`/`usuarios` (propiedad de Pasajeros/Seguridad) pero nunca
escribe ahí — este módulo solo resuelve el titular ya existente, no crea
perfiles de pasajero (ver nota de alcance en `plan.md`).
"""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class ReservasRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── pasajeros (lectura) ─────────────────────────────────────────────
    async def pasajero_de_usuario(self, usuario_id: str) -> dict | None:
        return await self._client.get_first("pasajeros", f'usuario_id="{usuario_id}"')

    async def pasajero_por_email(self, email: str) -> dict | None:
        safe = email.replace('"', '\\"')
        usuario = await self._client.get_first("usuarios", f'email="{safe}"')
        if usuario is None:
            return None
        return await self.pasajero_de_usuario(usuario["id"])

    # ── reservas ─────────────────────────────────────────────────────
    async def crear_reserva(self, data: dict) -> dict:
        return await self._client.create_record("reservas", data)

    async def obtener_reserva(self, reserva_id: str) -> dict | None:
        try:
            return await self._client.get_record("reservas", reserva_id)
        except PocketBaseError:
            return None

    async def actualizar_reserva(self, reserva_id: str, data: dict) -> dict:
        return await self._client.update_record("reservas", reserva_id, data)

    async def listar_reservas_de_pasajero(self, pasajero_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "reservas",
            {"filter": f'pasajero_titular_id="{pasajero_id}"', "sort": "-fecha_reserva", "perPage": 100},
        )
        return resultado["items"]

    async def listar_pendientes_vencidas(self, ahora_iso: str) -> list[dict]:
        resultado = await self._client.list_records(
            "reservas",
            {
                "filter": f'estado="pendiente_pago" && fecha_expiracion_pago<="{ahora_iso}"',
                "perPage": 200,
            },
        )
        return resultado["items"]

    # ── reserva_pasajeros ────────────────────────────────────────────
    async def agregar_pasajero(
        self, reserva_id: str, pasajero_id: str, tipo_pasajero: str = "adulto"
    ) -> dict:
        return await self._client.create_record(
            "reserva_pasajeros",
            {"reserva_id": reserva_id, "pasajero_id": pasajero_id, "tipo_pasajero": tipo_pasajero},
        )

    async def pasajeros_de_reserva(self, reserva_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "reserva_pasajeros", {"filter": f'reserva_id="{reserva_id}"', "perPage": 20}
        )
        return resultado["items"]

    # ── reserva_extras ───────────────────────────────────────────────
    async def agregar_extra(self, reserva_id: str, tipo: str, descripcion: str, precio: float) -> dict:
        return await self._client.create_record(
            "reserva_extras",
            {"reserva_id": reserva_id, "tipo": tipo, "descripcion": descripcion, "precio": precio},
        )

    async def extras_de_reserva(self, reserva_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "reserva_extras", {"filter": f'reserva_id="{reserva_id}"', "perPage": 20}
        )
        return resultado["items"]

    async def eliminar_extras_de_reserva(self, reserva_id: str) -> None:
        for extra in await self.extras_de_reserva(reserva_id):
            await self._client.delete_record("reserva_extras", extra["id"])

    # ── alertas_precio ───────────────────────────────────────────────
    async def crear_alerta(self, data: dict) -> dict:
        return await self._client.create_record("alertas_precio", data)

    async def listar_alertas_de_pasajero(self, pasajero_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "alertas_precio", {"filter": f'pasajero_id="{pasajero_id}"', "perPage": 100}
        )
        return resultado["items"]

    # ── configuración ────────────────────────────────────────────────
    async def config(self, clave: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        return await self._client.get_first("configuracion_sistema", f'clave="{safe}"')
