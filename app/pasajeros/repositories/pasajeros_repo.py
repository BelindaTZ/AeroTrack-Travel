"""`pasajeros`, `documentos_viaje`, `viajeros_frecuentes` — OPERACIONAL,
migrado a MinIO (`app/shared/minio_operational_client.py`, ver plan de
migración PASO 2/3). `usuarios` sigue en PocketBase (CONFIG, otro módulo)
— este repo sigue usando `PocketBaseClient` solo para esa lectura
cross-módulo. `reservas` (lectura, `reservas_de_pasajero`) migró a MinIO
en el paso 5 — ya no es PocketBase.

**Espejo de `pasajeros` en PocketBase (RC-OP-003)**: PocketBase valida
campos `relation` contra filas reales en su propia base — 15 colecciones
tenían un campo `relation` apuntando a `pasajeros`, y PocketBase 0.22 no
permite cambiar el tipo de un campo existente (`validation_field_type_change`).
Cada create/update de `pasajeros` en MinIO se espeja en silencio hacia la
colección `pasajeros` de PocketBase (mismo id, nunca se lee de vuelta) —
solo para que esas 15 colecciones sigan pudiendo crear/actualizar
registros sin romper la validación. **Estado (2026-07-25)**: de esas 15,
solo `newsletter_suscripciones` (módulo Ofertas) sigue sin migrar — es la
única razón por la que este espejo todavía no se puede eliminar. Cuando
migre, el espejo se elimina y `pasajeros` queda 100% en MinIO.
"""

import datetime

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client

ENTIDAD_PASAJEROS = "pasajeros"
ENTIDAD_DOCUMENTOS = "documentos_viaje"
ENTIDAD_VIAJEROS_FRECUENTES = "viajeros_frecuentes"


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


class PasajerosRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── pasajeros ─────────────────────────────────────────────────────
    async def crear_pasajero(self, data: dict) -> dict:
        """Usado por `UsuariosService.crear_pasajero` (RF-SEG-008, alta de
        cuenta) — Seguridad crea el perfil extendido junto con la cuenta,
        pero el dato en sí es propiedad de este módulo."""
        id_ = moc.generar_id()
        registro = {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}
        creado = await moc.crear(ENTIDAD_PASAJEROS, id_, registro)
        await self._client.create_record(ENTIDAD_PASAJEROS, {"id": id_, **data})
        return creado

    async def pasajero_de_usuario(self, usuario_id: str) -> dict | None:
        pasajeros = await moc.listar_todos(ENTIDAD_PASAJEROS)
        return next((p for p in pasajeros if p.get("usuario_id") == usuario_id), None)

    async def obtener_pasajero(self, pasajero_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_PASAJEROS, pasajero_id)

    async def actualizar_contacto(self, pasajero_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        actualizado = await moc.actualizar_con_reintento(ENTIDAD_PASAJEROS, pasajero_id, _mutar)
        await self._client.update_record(ENTIDAD_PASAJEROS, pasajero_id, data)
        return actualizado

    async def buscar_pasajeros(self, termino: str) -> list[dict]:
        termino_bajo = termino.lower()
        pasajeros = await moc.listar_todos(ENTIDAD_PASAJEROS)
        return [
            p for p in pasajeros
            if termino_bajo in (p.get("telefono") or "").lower()
            or termino_bajo in (p.get("contacto_emergencia") or "").lower()
        ]

    async def eliminar_pasajero(self, pasajero_id: str) -> None:
        await moc.eliminar(ENTIDAD_PASAJEROS, pasajero_id)
        try:
            await self._client.delete_record(ENTIDAD_PASAJEROS, pasajero_id)
        except PocketBaseError:
            pass  # espejo ya inconsistente o inexistente — no bloquea el borrado real (MinIO)

    # ── documentos_viaje (RF-PAS-005) ───────────────────────────────────
    async def documentos_de_pasajero(self, pasajero_id: str) -> list[dict]:
        documentos = await moc.listar_todos(ENTIDAD_DOCUMENTOS)
        resultado = [d for d in documentos if d.get("pasajero_id") == pasajero_id]
        resultado.sort(key=lambda d: d.get("created") or "", reverse=True)
        return resultado

    async def obtener_documento(self, documento_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_DOCUMENTOS, documento_id)

    async def crear_documento(self, data: dict) -> dict:
        id_ = moc.generar_id()
        registro = {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}
        return await moc.crear(ENTIDAD_DOCUMENTOS, id_, registro)

    async def eliminar_documento(self, documento_id: str) -> None:
        await moc.eliminar(ENTIDAD_DOCUMENTOS, documento_id)

    # ── viajeros_frecuentes (RF-PAS-006) ────────────────────────────────
    async def viajeros_frecuentes_de_pasajero(self, pasajero_id: str) -> list[dict]:
        viajeros = await moc.listar_todos(ENTIDAD_VIAJEROS_FRECUENTES)
        resultado = [v for v in viajeros if v.get("pasajero_id") == pasajero_id]
        resultado.sort(key=lambda v: v.get("nombre_completo") or "")
        return resultado

    async def obtener_viajero_frecuente(self, viajero_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_VIAJEROS_FRECUENTES, viajero_id)

    async def crear_viajero_frecuente(self, data: dict) -> dict:
        id_ = moc.generar_id()
        registro = {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}
        return await moc.crear(ENTIDAD_VIAJEROS_FRECUENTES, id_, registro)

    async def eliminar_viajero_frecuente(self, viajero_id: str) -> None:
        await moc.eliminar(ENTIDAD_VIAJEROS_FRECUENTES, viajero_id)

    # ── reportes (CU-T05, CU-T37 — lectura masiva) ──────────────────────
    async def listar_todos_pasajeros(self) -> list[dict]:
        return await moc.listar_todos(ENTIDAD_PASAJEROS)

    async def listar_todos_usuarios_pasajero(self) -> list[dict]:
        rol_pasajero = await self._client.get_first("roles", 'nombre="Pasajero"')
        if rol_pasajero is None:
            return []
        resultado = await self._client.list_records(
            "usuarios", {"filter": f'rol_id="{rol_pasajero["id"]}"', "perPage": 500}
        )
        return resultado["items"]

    # ── usuarios (lectura, CONFIG — sigue en PocketBase) ────────────────
    async def usuario_por_id(self, usuario_id: str) -> dict | None:
        try:
            return await self._client.get_record("usuarios", usuario_id)
        except PocketBaseError:
            return None

    async def buscar_usuarios(self, termino: str) -> list[dict]:
        safe = termino.replace('"', '\\"')
        resultado = await self._client.list_records(
            "usuarios",
            {
                "filter": f'nombre_completo~"{safe}" || email~"{safe}"',
                "perPage": 100,
            },
        )
        return resultado["items"]

    # ── reservas (lectura — OPERACIONAL, migrada a MinIO en paso 5) ──────
    async def reservas_de_pasajero(self, pasajero_id: str, estado: str | None = None) -> list[dict]:
        """`fecha_desde`/`fecha_hasta` NO se filtran aquí: son rango de fecha
        de *vuelo*, y `fecha_salida` vive en `vuelos_catalogo`, no en
        `reservas` — el filtro por rango de fecha se aplica en el servicio,
        una vez resuelto el vuelo de cada reserva."""
        reservas = await moc.listar_todos("reservas")
        resultado = [r for r in reservas if r.get("pasajero_titular_id") == pasajero_id]
        if estado:
            resultado = [r for r in resultado if r.get("estado") == estado]
        resultado.sort(key=lambda r: r.get("created") or "", reverse=True)
        return resultado
