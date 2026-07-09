"""Wrapper HTTP async genérico sobre la API REST de PocketBase (pocketbase-travel).

Sin conocimiento de ninguna colección específica — cada módulo lo consume a
través de su propio repository (p. ej. `app/seguridad/repositories/seguridad_repo.py`).
Reutilizable por los 6 módulos operativos para evitar duplicar la lógica de
autenticación admin y de armado de requests contra PocketBase.
"""

from typing import Any

import httpx

from app.shared.config import get_settings


class PocketBaseError(Exception):
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"PocketBase error {status_code}: {detail}")


class PocketBaseClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.pb_url.rstrip("/")
        self._admin_email = settings.pb_email
        self._admin_password = settings.pb_password
        self._admin_token: str | None = None

    async def _admin_auth_header(self) -> dict[str, str]:
        if self._admin_token is None:
            async with httpx.AsyncClient(base_url=self._base_url) as client:
                resp = await client.post(
                    "/api/admins/auth-with-password",
                    json={"identity": self._admin_email, "password": self._admin_password},
                )
                self._raise_for_status(resp)
                self._admin_token = resp.json()["token"]
        return {"Authorization": self._admin_token}

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            raise PocketBaseError(resp.status_code, detail)

    async def _headers(self, token: str | None) -> dict[str, str]:
        return {"Authorization": token} if token else await self._admin_auth_header()

    async def list_records(
        self,
        collection: str,
        params: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        headers = await self._headers(token)
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.get(
                f"/api/collections/{collection}/records", params=params, headers=headers
            )
            self._raise_for_status(resp)
            return resp.json()

    async def get_record(
        self, collection: str, record_id: str, token: str | None = None
    ) -> dict[str, Any]:
        headers = await self._headers(token)
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.get(
                f"/api/collections/{collection}/records/{record_id}", headers=headers
            )
            self._raise_for_status(resp)
            return resp.json()

    async def get_first(
        self, collection: str, filter_: str, token: str | None = None
    ) -> dict[str, Any] | None:
        result = await self.list_records(
            collection, params={"filter": filter_, "perPage": 1}, token=token
        )
        items = result.get("items", [])
        return items[0] if items else None

    async def create_record(
        self, collection: str, data: dict[str, Any], token: str | None = None
    ) -> dict[str, Any]:
        headers = await self._headers(token)
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post(
                f"/api/collections/{collection}/records", json=data, headers=headers
            )
            self._raise_for_status(resp)
            return resp.json()

    async def update_record(
        self,
        collection: str,
        record_id: str,
        data: dict[str, Any],
        token: str | None = None,
    ) -> dict[str, Any]:
        headers = await self._headers(token)
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.patch(
                f"/api/collections/{collection}/records/{record_id}",
                json=data,
                headers=headers,
            )
            self._raise_for_status(resp)
            return resp.json()

    async def update_record_con_archivo(
        self,
        collection: str,
        record_id: str,
        data: dict[str, Any],
        archivos: dict[str, tuple[str, bytes, str]],
        token: str | None = None,
    ) -> dict[str, Any]:
        """Como `update_record`, pero como multipart/form-data — necesario
        para escribir campos `file` (PocketBase no acepta binarios en JSON)."""
        headers = await self._headers(token)
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.patch(
                f"/api/collections/{collection}/records/{record_id}",
                data=data,
                files=archivos,
                headers=headers,
            )
            self._raise_for_status(resp)
            return resp.json()

    async def delete_record(
        self, collection: str, record_id: str, token: str | None = None
    ) -> None:
        headers = await self._headers(token)
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.delete(
                f"/api/collections/{collection}/records/{record_id}", headers=headers
            )
            self._raise_for_status(resp)

    async def descargar_archivo(
        self, collection: str, record_id: str, filename: str, token: str | None = None
    ) -> bytes:
        """Trae los bytes crudos de un campo `file` — las colecciones de
        Facturación no tienen viewRule pública, así que esto siempre pasa
        por el token admin (igual que el resto del cliente)."""
        headers = await self._headers(token)
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.get(
                f"/api/files/{collection}/{record_id}/{filename}", headers=headers
            )
            self._raise_for_status(resp)
            return resp.content

    async def auth_with_password(
        self, collection: str, identity: str, password: str
    ) -> dict[str, Any]:
        """Login contra una colección AUTH (p. ej. `usuarios`). Lanza PocketBaseError
        con status 400 si las credenciales son inválidas — el caller decide el mensaje."""
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post(
                f"/api/collections/{collection}/auth-with-password",
                json={"identity": identity, "password": password},
            )
            self._raise_for_status(resp)
            return resp.json()

    async def auth_refresh(self, collection: str, token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post(
                f"/api/collections/{collection}/auth-refresh",
                headers={"Authorization": token},
            )
            self._raise_for_status(resp)
            return resp.json()


_client: PocketBaseClient | None = None


def get_pocketbase_client() -> PocketBaseClient:
    global _client
    if _client is None:
        _client = PocketBaseClient()
    return _client
