"""Encapsula las 9 colecciones propias de Seguridad sobre PocketBase.

Usa `app/shared/pocketbase_client.py` (genérico) — este repository es el
único lugar del módulo que conoce nombres de colección y filtros PocketBase.
Se amplía fase a fase conforme cada servicio lo necesita.
"""

from typing import Any

from app.shared.pocketbase_client import PocketBaseClient, get_pocketbase_client

COL_USUARIOS = "usuarios"
COL_ROLES = "roles"
COL_MODULOS = "modulos"
COL_PERMISOS = "permisos"
COL_ROLES_PERMISOS = "roles_permisos"
COL_ROLES_PERMISOS_TABLAS = "roles_permisos_tablas"
COL_MODULO_TABLAS = "modulo_tablas"
COL_AUDITORIA = "auditoria"
COL_CONFIGURACION_SISTEMA = "configuracion_sistema"


class SeguridadRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── usuarios ─────────────────────────────────────────────────────────
    async def get_usuario_by_email(self, email: str) -> dict[str, Any] | None:
        safe_email = email.replace('"', '\\"')
        return await self._client.get_first(COL_USUARIOS, f'email="{safe_email}"')

    async def get_usuario(self, usuario_id: str, token: str | None = None) -> dict[str, Any]:
        return await self._client.get_record(COL_USUARIOS, usuario_id, token)

    async def create_usuario(
        self, data: dict[str, Any], token: str | None = None
    ) -> dict[str, Any]:
        return await self._client.create_record(COL_USUARIOS, data, token)

    async def update_usuario(
        self, usuario_id: str, data: dict[str, Any], token: str | None = None
    ) -> dict[str, Any]:
        return await self._client.update_record(COL_USUARIOS, usuario_id, data, token)

    async def list_usuarios(
        self, params: dict[str, Any] | None = None, token: str | None = None
    ) -> dict[str, Any]:
        return await self._client.list_records(COL_USUARIOS, params, token)

    async def get_usuario_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        return await self._client.get_first(COL_USUARIOS, f'reset_token_hash="{token_hash}"')

    # ── autenticación ────────────────────────────────────────────────────
    async def auth_usuario(self, email: str, password: str) -> dict[str, Any]:
        return await self._client.auth_with_password(COL_USUARIOS, email, password)

    # ── configuración del sistema ───────────────────────────────────────
    async def get_config(self, clave: str, token: str | None = None) -> dict[str, Any] | None:
        safe_clave = clave.replace('"', '\\"')
        return await self._client.get_first(
            COL_CONFIGURACION_SISTEMA, f'clave="{safe_clave}"', token
        )

    # ── auditoría ────────────────────────────────────────────────────────
    async def insertar_auditoria(
        self, data: dict[str, Any], token: str | None = None
    ) -> dict[str, Any]:
        return await self._client.create_record(COL_AUDITORIA, data, token)

    async def list_auditoria(
        self, filtro: str | None = None, page: int = 1, per_page: int = 50
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"sort": "-created", "page": page, "perPage": per_page}
        if filtro:
            params["filter"] = filtro
        return await self._client.list_records(COL_AUDITORIA, params)
