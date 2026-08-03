"""`favoritos`, `viajes_personalizados`, `busquedas_recientes`,
`programa_beneficios_movimientos` son OPERACIONAL — migradas a MinIO (ver
plan de migración). `programa_beneficios_niveles` es CONFIG (catálogo de
niveles, estático) — sigue en PocketBase. La escritura de
`busquedas_recientes` la sigue haciendo cada módulo de producto vía
`app.shared.busqueda_reciente` (RN-CTA-001), no este repo.

Ninguna de las 4 entidades operacionales tiene relation fields hacia
colecciones todavía-no-migradas más allá de `pasajeros` (ya resuelto con
espejo, RC-OP-003) y `reservas` (`programa_beneficios_movimientos.reserva_id`,
opcional — confirmado en el barrido de la sesión, no bloquea)."""

import datetime

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseClient, get_pocketbase_client

ENTIDAD_FAVORITOS = "favoritos"
ENTIDAD_VIAJES_PERSONALIZADOS = "viajes_personalizados"
ENTIDAD_BUSQUEDAS_RECIENTES = "busquedas_recientes"
ENTIDAD_MOVIMIENTOS = "programa_beneficios_movimientos"


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


class CuentaRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── favoritos ────────────────────────────────────────────────────
    async def crear_favorito(self, pasajero_id: str, tipo: str, producto_ref: str, fecha_iso: str) -> dict:
        id_ = moc.generar_id()
        registro = {
            "id": id_, "created": fecha_iso, "updated": fecha_iso,
            "pasajero_id": pasajero_id, "tipo": tipo, "producto_ref": producto_ref, "fecha_guardado": fecha_iso,
        }
        return await moc.crear(ENTIDAD_FAVORITOS, id_, registro)

    async def listar_favoritos(self, pasajero_id: str) -> list[dict]:
        favoritos = await moc.listar_todos(ENTIDAD_FAVORITOS)
        resultado = [f for f in favoritos if f.get("pasajero_id") == pasajero_id]
        resultado.sort(key=lambda f: f.get("fecha_guardado") or "", reverse=True)
        return resultado

    async def obtener_favorito(self, favorito_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_FAVORITOS, favorito_id)

    async def eliminar_favorito(self, favorito_id: str) -> None:
        await moc.eliminar(ENTIDAD_FAVORITOS, favorito_id)

    # ── viajes_personalizados ────────────────────────────────────────
    async def crear_viaje_personalizado(self, pasajero_id: str, nombre: str, descripcion: str | None) -> dict:
        id_ = moc.generar_id()
        registro = {
            "id": id_, "created": _timestamp(), "updated": _timestamp(),
            "pasajero_id": pasajero_id, "nombre": nombre, "descripcion": descripcion or "",
        }
        return await moc.crear(ENTIDAD_VIAJES_PERSONALIZADOS, id_, registro)

    async def listar_viajes_personalizados(self, pasajero_id: str) -> list[dict]:
        viajes = await moc.listar_todos(ENTIDAD_VIAJES_PERSONALIZADOS)
        resultado = [v for v in viajes if v.get("pasajero_id") == pasajero_id]
        resultado.sort(key=lambda v: v.get("created") or "", reverse=True)
        return resultado

    async def eliminar_viaje_personalizado(self, viaje_id: str) -> None:
        await moc.eliminar(ENTIDAD_VIAJES_PERSONALIZADOS, viaje_id)

    async def obtener_viaje_personalizado(self, viaje_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_VIAJES_PERSONALIZADOS, viaje_id)

    # ── busquedas_recientes (lectura — RN-CTA-001: cada módulo de
    #    producto es quien escribe, ver app.shared.busqueda_reciente) ──
    async def listar_busquedas_recientes(self, pasajero_id: str, limite: int = 20) -> list[dict]:
        busquedas = await moc.listar_todos(ENTIDAD_BUSQUEDAS_RECIENTES)
        resultado = [b for b in busquedas if b.get("pasajero_id") == pasajero_id]
        resultado.sort(key=lambda b: b.get("fecha") or "", reverse=True)
        return resultado[:limite]

    async def obtener_busqueda_reciente(self, busqueda_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_BUSQUEDAS_RECIENTES, busqueda_id)

    async def listar_todas_busquedas(self) -> list[dict]:
        """ETL comercial (Fase B, sesión 2026-08-02) — todas las búsquedas
        sin acotar a un pasajero, para `total_busquedas` del funnel de
        conversión. Nota: solo captura búsquedas de un pasajero con sesión
        iniciada (RN-CTA-001) — navegación anónima no queda registrada acá,
        así que es un piso, no el volumen real de búsquedas del sitio."""
        return await moc.listar_todos(ENTIDAD_BUSQUEDAS_RECIENTES)

    # ── programa de beneficios ───────────────────────────────────────
    async def movimientos_de_pasajero(self, pasajero_id: str) -> list[dict]:
        movimientos = await moc.listar_todos(ENTIDAD_MOVIMIENTOS)
        resultado = [m for m in movimientos if m.get("pasajero_id") == pasajero_id]
        resultado.sort(key=lambda m: m.get("fecha") or "", reverse=True)
        return resultado

    async def niveles_programa_beneficios(self) -> list[dict]:
        resultado = await self._client.list_records(
            "programa_beneficios_niveles", {"sort": "puntos_minimos", "perPage": 50}
        )
        return resultado["items"]

    async def crear_nivel_beneficio(self, data: dict) -> dict:
        return await self._client.create_record("programa_beneficios_niveles", data)

    async def actualizar_nivel_beneficio(self, nivel_id: str, data: dict) -> dict:
        return await self._client.update_record("programa_beneficios_niveles", nivel_id, data)

    # ── favoritos (CU-T55, reporte agregado — Comercial) ────────────────
    async def listar_todos_favoritos(self) -> list[dict]:
        return await moc.listar_todos(ENTIDAD_FAVORITOS)
