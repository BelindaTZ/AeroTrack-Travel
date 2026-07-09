"""RF-SEG-010,011,012 — crear/editar/eliminar rol. RN-SEG-007,008,009."""

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.shared.pocketbase_client import PocketBaseClient, get_pocketbase_client


class RolProtegido(Exception):
    pass


class RolConUsuariosAsignados(Exception):
    def __init__(self, cantidad: int):
        self.cantidad = cantidad
        super().__init__(f"{cantidad} usuario(s) activos asignados")


class NivelDosExcedeNivelUno(Exception):
    def __init__(self, modulo_id: str):
        self.modulo_id = modulo_id


class RolesService:
    def __init__(
        self, repo: SeguridadRepository | None = None, client: PocketBaseClient | None = None
    ) -> None:
        self._repo = repo or SeguridadRepository()
        self._client = client or get_pocketbase_client()

    # ── RF-SEG-010 ───────────────────────────────────────────────────────
    async def crear_rol(self, nombre: str, descripcion: str) -> dict:
        return await self._client.create_record(
            "roles", {"nombre": nombre, "descripcion": descripcion, "es_sistema": False}
        )

    async def listar_roles(self) -> list[dict]:
        result = await self._client.list_records("roles", {"perPage": 200, "sort": "nombre"})
        return result["items"]

    async def obtener_rol(self, rol_id: str) -> dict:
        return await self._client.get_record("roles", rol_id)

    async def matriz_actual(self, rol_id: str) -> dict:
        nivel1 = await self._client.list_records(
            "roles_permisos", {"filter": f'rol_id="{rol_id}"', "perPage": 500}
        )
        nivel2 = await self._client.list_records(
            "roles_permisos_tablas", {"filter": f'rol_id="{rol_id}"', "perPage": 500}
        )
        return {
            "permiso_ids": {rp["permiso_id"] for rp in nivel1["items"]},
            "tablas": {(rpt["modulo_id"], rpt["tabla"]) for rpt in nivel2["items"]},
        }

    # ── RF-SEG-011 ───────────────────────────────────────────────────────
    async def editar_rol(
        self,
        rol_id: str,
        nombre: str | None,
        descripcion: str | None,
        permiso_ids: list[str],
        tablas_nivel2: list[tuple[str, str]],
    ) -> dict:
        """Reemplaza la matriz completa Nivel1/Nivel2 del rol.

        RN-SEG-009: cada (modulo_id, tabla) de Nivel 2 solo se acepta si el
        rol conserva, en esta misma edición, al menos un permiso Nivel 1
        sobre ese módulo — Nivel 2 nunca amplía lo no autorizado en Nivel 1.
        """
        modulos_autorizados_nivel1: set[str] = set()
        if permiso_ids:
            filtro = " || ".join(f'id="{pid}"' for pid in permiso_ids)
            permisos = await self._client.list_records("permisos", {"filter": filtro, "perPage": 500})
            modulos_autorizados_nivel1 = {p["modulo_id"] for p in permisos["items"]}

        for modulo_id, _tabla in tablas_nivel2:
            if modulo_id not in modulos_autorizados_nivel1:
                raise NivelDosExcedeNivelUno(modulo_id)

        campos: dict = {}
        if nombre is not None:
            campos["nombre"] = nombre
        if descripcion is not None:
            campos["descripcion"] = descripcion
        if campos:
            await self._client.update_record("roles", rol_id, campos)

        await self._reemplazar_nivel1(rol_id, permiso_ids)
        await self._reemplazar_nivel2(rol_id, tablas_nivel2)

        return await self.obtener_rol(rol_id)

    async def _reemplazar_nivel1(self, rol_id: str, permiso_ids: list[str]) -> None:
        actuales = await self._client.list_records(
            "roles_permisos", {"filter": f'rol_id="{rol_id}"', "perPage": 500}
        )
        actuales_por_permiso = {item["permiso_id"]: item["id"] for item in actuales["items"]}
        deseados = set(permiso_ids)
        for permiso_id, item_id in actuales_por_permiso.items():
            if permiso_id not in deseados:
                await self._client.delete_record("roles_permisos", item_id)
        for permiso_id in deseados - set(actuales_por_permiso.keys()):
            await self._client.create_record(
                "roles_permisos", {"rol_id": rol_id, "permiso_id": permiso_id}
            )

    async def _reemplazar_nivel2(self, rol_id: str, tablas_nivel2: list[tuple[str, str]]) -> None:
        actuales = await self._client.list_records(
            "roles_permisos_tablas", {"filter": f'rol_id="{rol_id}"', "perPage": 500}
        )
        actuales_por_clave = {(item["modulo_id"], item["tabla"]): item["id"] for item in actuales["items"]}
        deseados = set(tablas_nivel2)
        for clave, item_id in actuales_por_clave.items():
            if clave not in deseados:
                await self._client.delete_record("roles_permisos_tablas", item_id)
        for modulo_id, tabla in deseados - set(actuales_por_clave.keys()):
            await self._client.create_record(
                "roles_permisos_tablas", {"rol_id": rol_id, "modulo_id": modulo_id, "tabla": tabla}
            )

    # ── RF-SEG-012 ───────────────────────────────────────────────────────
    async def eliminar_rol(self, rol_id: str) -> None:
        rol = await self.obtener_rol(rol_id)
        if rol.get("es_sistema"):
            raise RolProtegido()

        usuarios_asignados = await self._client.list_records(
            "usuarios", {"filter": f'rol_id="{rol_id}" && activo=true', "perPage": 1}
        )
        cantidad = usuarios_asignados.get("totalItems", 0)
        if cantidad > 0:
            raise RolConUsuariosAsignados(cantidad)

        await self._client.delete_record("roles", rol_id)
