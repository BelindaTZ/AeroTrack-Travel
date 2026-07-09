from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.seguridad.services.rbac_service import requiere_permiso
from app.seguridad.services.session_service import COOKIE_NAME


def _dummy_app(modulo: str, accion: str, tabla: str | None = None) -> FastAPI:
    dummy = FastAPI()

    @dummy.get("/protegido")
    async def protegido(usuario: dict = Depends(requiere_permiso(modulo, accion, tabla))):
        return {"id": usuario["id"]}

    from app.seguridad.services.rbac_service import AccesoDenegado
    from fastapi.responses import JSONResponse

    @dummy.exception_handler(AccesoDenegado)
    async def handler(request, exc: AccesoDenegado):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return dummy


async def _login_token(client, usuario) -> str:
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    return resp.cookies[COOKIE_NAME]


# ── Nivel 1 (CHK017) ──────────────────────────────────────────────────────

async def test_requiere_permiso_bloquea_sin_nivel1(client, usuario_factory, rol_agente):
    # El rol Agente no tiene ningún permiso sobre el módulo "seguridad" en la
    # matriz sembrada (roles_permisos) -> Nivel 1 falla.
    usuario = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])
    token = await _login_token(client, usuario)

    transport = ASGITransport(app=_dummy_app("seguridad", "eliminar"))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/protegido", cookies={COOKIE_NAME: token})
    assert resp.status_code == 403


async def test_requiere_permiso_permite_con_nivel1(client, usuario_factory, rol_administrador):
    usuario = await usuario_factory(tipo_actor="administrador", rol_id=rol_administrador["id"])
    token = await _login_token(client, usuario)

    transport = ASGITransport(app=_dummy_app("seguridad", "ver"))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/protegido", cookies={COOKIE_NAME: token})
    assert resp.status_code == 200
    assert resp.json()["id"] == usuario["id"]


async def test_requiere_permiso_bloquea_sin_rol(client, usuario_factory):
    usuario = await usuario_factory(tipo_actor="pasajero", rol_id=None)
    token = await _login_token(client, usuario)

    transport = ASGITransport(app=_dummy_app("seguridad", "ver"))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/protegido", cookies={COOKIE_NAME: token})
    assert resp.status_code == 403


# ── Nivel 2 nunca amplía Nivel 1 (RN-SEG-009, CHK031) ───────────────────

async def test_nivel2_nunca_amplia_nivel1(client, usuario_factory, rol_agente, pb):
    # Fila de Nivel 2 "errónea": el rol Agente NO tiene Nivel 1 sobre
    # "seguridad", pero igual se le agrega una restricción de tabla ahí.
    # Debe seguir bloqueado: Nivel 1 se evalúa primero y nunca se llega a
    # consultar Nivel 2 si Nivel 1 ya falló.
    modulo_seguridad = await pb.get_first("modulos", 'clave="seguridad"')
    fila_nivel2 = await pb.create_record(
        "roles_permisos_tablas",
        {"rol_id": rol_agente["id"], "modulo_id": modulo_seguridad["id"], "tabla": "usuarios"},
    )
    try:
        usuario = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])
        token = await _login_token(client, usuario)

        transport = ASGITransport(app=_dummy_app("seguridad", "ver", tabla="usuarios"))
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/protegido", cookies={COOKIE_NAME: token})
        assert resp.status_code == 403
    finally:
        await pb.delete_record("roles_permisos_tablas", fila_nivel2["id"])
