"""Wrapper HTTP async genérico sobre la API REST de PocketBase (pocketbase-travel).

Sin conocimiento de ninguna colección específica — cada módulo lo consume a
través de su propio repository (p. ej. `app/seguridad/repositories/seguridad_repo.py`).
Reutilizable por los 6 módulos operativos para evitar duplicar la lógica de
autenticación admin y de armado de requests contra PocketBase.

**Un solo `httpx.AsyncClient` reutilizado por toda la vida del proceso**
(antes: uno nuevo por cada llamada). Medido en vivo al implementar el mapa
de asientos (RF-VUE-011, que hace ráfagas de ~180 creates): 180 requests
secuenciales con cliente nuevo cada vez tardaban ~90s reales (≈480ms/req);
el mismo cliente reutilizado hace 20 requests en 0.48s (≈24ms/req) — el
costo no es la red/PocketBase (confirmado con curl puro, ~68ms para 10
requests), es abrir/cerrar el `AsyncClient` en cada llamada. `httpx.AsyncClient`
está diseñado para compartirse entre corrutinas concurrentes (pool de
conexiones propio), así que esto es más correcto, no solo más rápido — y
como `get_pocketbase_client()` ya es un singleton de proceso, un solo
cliente persistente es exactamente lo que corresponde.
"""

import asyncio
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
        self._http_client: httpx.AsyncClient | None = None
        self._http_loop: asyncio.AbstractEventLoop | None = None

    @property
    def _http(self) -> httpx.AsyncClient:
        # `get_pocketbase_client()` es un singleton de proceso, pero la
        # suite de tests corre cada test en un event loop nuevo
        # (`asyncio_default_fixture_loop_scope = function`, pytest.ini) — un
        # `httpx.AsyncClient` creado en un loop ya cerrado revienta al
        # reusarse en el siguiente test. Se recrea si el loop cambió; en
        # producción (un solo loop de principio a fin) esto se resuelve una
        # sola vez y queda igual de rápido que un cliente fijo.
        loop = asyncio.get_running_loop()
        if self._http_client is None or self._http_loop is not loop:
            self._http_client = httpx.AsyncClient(base_url=self._base_url)
            self._http_loop = loop
        return self._http_client

    async def _admin_auth_header(self) -> dict[str, str]:
        if self._admin_token is None:
            resp = await self._http.post(
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
        resp = await self._http.get(
            f"/api/collections/{collection}/records", params=params, headers=headers
        )
        self._raise_for_status(resp)
        return resp.json()

    async def get_record(
        self, collection: str, record_id: str, token: str | None = None
    ) -> dict[str, Any]:
        headers = await self._headers(token)
        resp = await self._http.get(
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
        resp = await self._http.post(
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
        resp = await self._http.patch(
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
        resp = await self._http.patch(
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
        resp = await self._http.delete(
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
        resp = await self._http.get(f"/api/files/{collection}/{record_id}/{filename}", headers=headers)
        self._raise_for_status(resp)
        return resp.content

    async def auth_with_password(
        self, collection: str, identity: str, password: str
    ) -> dict[str, Any]:
        """Login contra una colección AUTH (p. ej. `usuarios`). Lanza PocketBaseError
        con status 400 si las credenciales son inválidas — el caller decide el mensaje."""
        resp = await self._http.post(
            f"/api/collections/{collection}/auth-with-password",
            json={"identity": identity, "password": password},
        )
        self._raise_for_status(resp)
        return resp.json()

    async def auth_refresh(self, collection: str, token: str) -> dict[str, Any]:
        resp = await self._http.post(
            f"/api/collections/{collection}/auth-refresh",
            headers={"Authorization": token},
        )
        self._raise_for_status(resp)
        return resp.json()

    async def list_auth_methods(self, collection: str) -> dict[str, Any]:
        resp = await self._http.get(f"/api/collections/{collection}/auth-methods")
        self._raise_for_status(resp)
        return resp.json()

    async def auth_with_oauth2(
        self,
        collection: str,
        provider: str,
        code: str,
        code_verifier: str,
        redirect_url: str,
        create_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Completa el flujo OAuth2 (código de Google + PKCE) contra una
        colección AUTH. `create_data` solo aplica si PocketBase crea un
        registro nuevo (primer login con ese proveedor)."""
        payload: dict[str, Any] = {
            "provider": provider,
            "code": code,
            "codeVerifier": code_verifier,
            "redirectUrl": redirect_url,
        }
        if create_data:
            payload["createData"] = create_data
        resp = await self._http.post(f"/api/collections/{collection}/auth-with-oauth2", json=payload)
        self._raise_for_status(resp)
        return resp.json()


_client: PocketBaseClient | None = None


def get_pocketbase_client() -> PocketBaseClient:
    global _client
    if _client is None:
        _client = PocketBaseClient()
    return _client
