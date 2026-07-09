from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse
from httpx import ASGITransport, AsyncClient

from app.seguridad.services.session_service import COOKIE_NAME, SesionExpirada, verificar_sesion


# ── CU-O01 / RF-SEG-001 (CHK001-003) ─────────────────────────────────────

async def test_login_credenciales_correctas_emite_token_y_redirige(client, usuario_factory):
    usuario = await usuario_factory(tipo_actor="pasajero")
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/mi-perfil"
    assert COOKIE_NAME in resp.cookies


async def test_login_admin_redirige_a_panel_admin(client, usuario_factory, rol_administrador):
    usuario = await usuario_factory(tipo_actor="administrador", rol_id=rol_administrador["id"])
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/usuarios"


async def test_login_credenciales_incorrectas_mensaje_generico(client, usuario_factory):
    usuario = await usuario_factory()
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": "clave-incorrecta"}
    )
    assert resp.status_code == 401
    assert "Credenciales incorrectas" in resp.text
    assert COOKIE_NAME not in resp.cookies


async def test_login_cuenta_inactiva(client, usuario_factory):
    usuario = await usuario_factory(activo=False)
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 403
    assert "Cuenta desactivada" in resp.text
    assert COOKIE_NAME not in resp.cookies


# ── CU-O02 / RF-SEG-002 (CHK004) ─────────────────────────────────────────

async def test_logout_invalida_y_redirige(client):
    resp = await client.post("/logout")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"
    assert COOKIE_NAME in resp.headers.get("set-cookie", "")


# ── CU-O42 / RF-SEG-003 (CHK005, CHK006) ─────────────────────────────────
# `verificar_sesion` se prueba montado en una app FastAPI mínima, propia del
# test: es un servicio transversal sin router propio en Fase 1.

def _dummy_app() -> FastAPI:
    dummy = FastAPI()

    @dummy.get("/protegido")
    async def protegido(usuario: dict = Depends(verificar_sesion)):
        return {"id": usuario["id"]}

    @dummy.exception_handler(SesionExpirada)
    async def handler(request, exc: SesionExpirada):
        location = "/login"
        if exc.next_path:
            location += f"?next={exc.next_path}"
        return RedirectResponse(location, status_code=303)

    return dummy


async def test_verificar_sesion_rechaza_token_invalido():
    transport = ASGITransport(app=_dummy_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/protegido", cookies={COOKIE_NAME: "token-invalido"})
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login?next=/protegido"


async def test_verificar_sesion_sin_cookie_preserva_ruta_y_query_del_flujo():
    transport = ASGITransport(app=_dummy_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/protegido?paso=2")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login?next=/protegido?paso=2"


async def test_verificar_sesion_token_valido_permite_acceso(client, usuario_factory):
    usuario = await usuario_factory()
    login_resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    token = login_resp.cookies[COOKIE_NAME]

    transport = ASGITransport(app=_dummy_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/protegido", cookies={COOKIE_NAME: token})
    assert resp.status_code == 200
    assert resp.json()["id"] == usuario["id"]


# ── RN-SEG-001: todo intento de login, exitoso o fallido, se audita ─────

async def test_login_exitoso_queda_auditado(client, usuario_factory, pb):
    usuario = await usuario_factory()
    await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    registro = await pb.get_first(
        "auditoria", f'accion="login" && registro_id="{usuario["id"]}"'
    )
    assert registro is not None
    await pb.delete_record("auditoria", registro["id"])


async def test_login_fallido_queda_auditado(client, usuario_factory, pb):
    usuario = await usuario_factory()
    await client.post("/login", data={"email": usuario["email"], "password": "clave-mala"})
    registro = await pb.get_first(
        "auditoria", f'accion="login_fallido" && detalle.email="{usuario["email"]}"'
    )
    # PocketBase no siempre soporta filtrar por clave dentro de JSON de la
    # misma forma entre versiones; si el filtro anterior no matchea, se
    # confirma igual buscando por accion+tabla y revisando el detalle en Python.
    if registro is None:
        recientes = await pb.list_records(
            "auditoria", {"filter": 'accion="login_fallido"', "sort": "-created", "perPage": 10}
        )
        registro = next(
            (r for r in recientes["items"] if r.get("detalle", {}).get("email") == usuario["email"]),
            None,
        )
    assert registro is not None
    await pb.delete_record("auditoria", registro["id"])


async def test_logout_queda_auditado(client, usuario_factory, pb):
    usuario = await usuario_factory()
    await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    await client.post("/logout")
    registro = await pb.get_first("auditoria", f'accion="logout" && registro_id="{usuario["id"]}"')
    assert registro is not None
    await pb.delete_record("auditoria", registro["id"])
