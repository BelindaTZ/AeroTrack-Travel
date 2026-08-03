"""`articulos_ayuda` es CONFIG (contenido tipo CMS, admin-managed) — sigue
en PocketBase. `articulo_calificaciones`/`casos_escalados` son OPERACIONAL
(interacción real de usuarios) — migradas a MinIO (ver plan de migración).
Ninguna de las dos tiene relation fields hacia colecciones todavía-no-
migradas más allá de `pasajeros` (ya resuelto con espejo, RC-OP-003) y
`articulos_ayuda`/`usuarios` (CONFIG, sin riesgo) — confirmado en el
barrido de relation fields de la sesión."""

import datetime

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client

ENTIDAD_CALIFICACIONES = "articulo_calificaciones"
ENTIDAD_CASOS = "casos_escalados"


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


class CentroAyudaRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── articulos_ayuda (CONFIG, sigue en PocketBase) ────────────────
    async def buscar_articulos(self, termino: str | None, categoria: str | None) -> list[dict]:
        condiciones = ['activo=true']
        if categoria:
            safe = categoria.replace('"', '\\"')
            condiciones.append(f'categoria="{safe}"')
        if termino:
            safe = termino.replace('"', '\\"')
            condiciones.append(f'(titulo~"{safe}" || contenido~"{safe}")')
        resultado = await self._client.list_records(
            "articulos_ayuda", {"filter": " && ".join(condiciones), "sort": "-fecha_publicacion", "perPage": 100}
        )
        return resultado["items"]

    async def obtener_articulo(self, articulo_id: str) -> dict | None:
        try:
            return await self._client.get_record("articulos_ayuda", articulo_id)
        except PocketBaseError:
            return None

    async def categorias_disponibles(self) -> list[str]:
        resultado = await self._client.list_records("articulos_ayuda", {"filter": "activo=true", "perPage": 200})
        return sorted({a["categoria"] for a in resultado["items"] if a.get("categoria")})

    async def listar_articulos_admin(self) -> list[dict]:
        """Incluye archivados — el Administrador gestiona ambos estados (RN-AYU-T01)."""
        resultado = await self._client.list_records("articulos_ayuda", {"sort": "-fecha_publicacion", "perPage": 200})
        return resultado["items"]

    async def listar_articulos_admin_filtrado(
        self, categoria: str | None = None, estado: str | None = None, texto: str | None = None
    ) -> list[dict]:
        """WP-05 (auditoría de WorkPanels) — igual que `listar_articulos_admin`
        pero con filtros. A diferencia de `buscar_articulos` (portal), acá NO
        se fuerza `activo=true`: el admin gestiona ambos estados (RN-AYU-T01)."""
        condiciones = []
        if categoria:
            safe = categoria.replace('"', '\\"')
            condiciones.append(f'categoria="{safe}"')
        if estado == "activo":
            condiciones.append("activo=true")
        elif estado == "archivado":
            condiciones.append("activo=false")
        if texto:
            safe = texto.replace('"', '\\"')
            condiciones.append(f'titulo~"{safe}"')

        params: dict = {"sort": "-fecha_publicacion", "perPage": 200}
        if condiciones:
            params["filter"] = " && ".join(condiciones)
        resultado = await self._client.list_records("articulos_ayuda", params)
        return resultado["items"]

    async def crear_articulo(self, data: dict) -> dict:
        return await self._client.create_record("articulos_ayuda", data)

    async def actualizar_articulo(self, articulo_id: str, data: dict) -> dict:
        return await self._client.update_record("articulos_ayuda", articulo_id, data)

    # ── articulo_calificaciones (OPERACIONAL, MinIO) ─────────────────
    async def crear_calificacion(self, articulo_id: str, pasajero_id: str | None, util: str, fecha_iso: str) -> dict:
        data = {"articulo_id": articulo_id, "util": util, "fecha": fecha_iso}
        if pasajero_id:
            data["pasajero_id"] = pasajero_id
        id_ = moc.generar_id()
        registro = {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}
        return await moc.crear(ENTIDAD_CALIFICACIONES, id_, registro)

    async def calificaciones_de_articulo(self, articulo_id: str) -> list[dict]:
        calificaciones = await moc.listar_todos(ENTIDAD_CALIFICACIONES)
        return [c for c in calificaciones if c.get("articulo_id") == articulo_id]

    async def todas_las_calificaciones(self) -> list[dict]:
        return await moc.listar_todos(ENTIDAD_CALIFICACIONES)

    # ── casos_escalados (OPERACIONAL, MinIO) ─────────────────────────
    async def crear_caso(self, data: dict) -> dict:
        id_ = moc.generar_id()
        registro = {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}
        return await moc.crear(ENTIDAD_CASOS, id_, registro)

    async def listar_casos(
        self, estado: str | None = None, desde: str | None = None, hasta: str | None = None
    ) -> list[dict]:
        """`desde`/`hasta` (IS-13, auditoría de informes simples, sesión
        2026-08-01) filtran por `fecha_creacion` — antes no había forma de
        acotar la bandeja a un período, solo por estado."""
        casos = await moc.listar_todos(ENTIDAD_CASOS)
        if estado:
            casos = [c for c in casos if c.get("estado") == estado]
        if desde:
            casos = [c for c in casos if (c.get("fecha_creacion") or "") >= desde]
        if hasta:
            casos = [c for c in casos if (c.get("fecha_creacion") or "") <= hasta]
        casos.sort(key=lambda c: c.get("fecha_creacion") or "", reverse=True)
        return casos

    async def obtener_caso(self, caso_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_CASOS, caso_id)

    async def actualizar_caso(self, caso_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_CASOS, caso_id, _mutar)

    async def casos_en_periodo(self, desde_iso: str) -> list[dict]:
        casos = await moc.listar_todos(ENTIDAD_CASOS)
        return [c for c in casos if (c.get("fecha_creacion") or "") >= desde_iso]
