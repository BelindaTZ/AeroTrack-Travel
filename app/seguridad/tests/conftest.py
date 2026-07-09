import uuid

import httpx
import pytest
from httpx import ASGITransport

from app.main import app
from app.shared.pocketbase_client import get_pocketbase_client

DEFAULT_PASSWORD = "ClaveSegura#123"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def pb():
    return get_pocketbase_client()


@pytest.fixture
async def usuario_factory(pb):
    """Crea usuarios de PocketBase desechables para pruebas; los borra al finalizar."""
    creados: list[str] = []

    async def _crear(
        tipo_actor: str = "pasajero",
        activo: bool = True,
        rol_id: str | None = None,
        password: str = DEFAULT_PASSWORD,
        **extra,
    ) -> dict:
        email = f"test.{uuid.uuid4().hex[:10]}@aerotrack.test"
        data = {
            "email": email,
            "password": password,
            "passwordConfirm": password,
            "nombre_completo": "Usuario de Prueba",
            "tipo_actor": tipo_actor,
            "activo": activo,
            "emailVisibility": True,
            "verified": True,
        }
        if rol_id:
            data["rol_id"] = rol_id
        data.update(extra)
        record = await pb.create_record("usuarios", data)
        record["_password"] = password
        creados.append(record["id"])
        return record

    yield _crear

    for usuario_id in creados:
        try:
            await pb.delete_record("usuarios", usuario_id)
        except Exception:
            pass


@pytest.fixture
async def rol_administrador(pb):
    rol = await pb.get_first("roles", 'nombre="Administrador"')
    assert rol is not None, "seed_seguridad.py debe correrse antes de la suite de tests"
    return rol


@pytest.fixture
async def rol_agente(pb):
    rol = await pb.get_first("roles", 'nombre="Agente"')
    assert rol is not None, "seed_seguridad.py debe correrse antes de la suite de tests"
    return rol


@pytest.fixture
async def admin_client(client, usuario_factory, rol_administrador):
    """Cliente ya autenticado como Administrador (rol sembrado, permisos completos)."""
    usuario = await usuario_factory(tipo_actor="administrador", rol_id=rol_administrador["id"])
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    client.admin_usuario = usuario
    return client
