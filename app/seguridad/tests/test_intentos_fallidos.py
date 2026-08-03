"""RF-SEG-T01 (Táctico) — dashboard de intentos de login fallidos +
"expiración forzada" (desactivar cuenta)."""

import datetime

import httpx
import pytest
from httpx import ASGITransport

from app.main import app
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.intentos_fallidos_service import (
    CuentaNoEncontrada,
    desactivar_cuenta_por_email,
    resumen_intentos_fallidos,
)


async def _limpiar(pb, emails: list[str]):
    todos = (await pb.list_records(
        "auditoria", {"filter": 'accion="login_fallido"', "perPage": 200}
    ))["items"]
    for registro in todos:
        if (registro.get("detalle") or {}).get("email") in emails:
            await pb.delete_record("auditoria", registro["id"])


async def test_resumen_agrupa_por_email_y_marca_sospechoso(pb):
    email = "ataque-fuerza-bruta@aerotrack.test"
    audit = AuditService()
    for _ in range(6):
        await audit.insertar("login_fallido", "usuarios", detalle={"email": email}, ip="10.0.0.1")

    filas = await resumen_intentos_fallidos(horas=1, umbral_sospechoso=5)
    fila = next(f for f in filas if f["identificador"] == email)
    assert fila["intentos"] == 6
    assert fila["sospechoso"] is True
    assert fila["ips"] == ["10.0.0.1"]

    await _limpiar(pb, [email])


async def test_resumen_no_marca_sospechoso_bajo_el_umbral(pb):
    email = "intento-normal@aerotrack.test"
    await AuditService().insertar("login_fallido", "usuarios", detalle={"email": email}, ip="10.0.0.2")

    filas = await resumen_intentos_fallidos(horas=1, umbral_sospechoso=5)
    fila = next(f for f in filas if f["identificador"] == email)
    assert fila["intentos"] == 1
    assert fila["sospechoso"] is False

    await _limpiar(pb, [email])


async def test_resumen_respeta_ventana_de_tiempo(pb):
    email = "fuera-de-ventana@aerotrack.test"
    await AuditService().insertar("login_fallido", "usuarios", detalle={"email": email}, ip="10.0.0.3")

    # "ahora" 48h en el futuro respecto al registro recién creado -> con una
    # ventana de 24h, ese intento queda fuera del corte.
    futuro = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=48)
    filas = await resumen_intentos_fallidos(horas=24, ahora=futuro)
    assert not any(f["identificador"] == email for f in filas)

    await _limpiar(pb, [email])


async def test_google_oauth_fallido_sin_email_se_agrupa_por_ip(pb):
    await AuditService().insertar("login_fallido", "usuarios", detalle={"metodo": "google"}, ip="10.0.0.4")

    filas = await resumen_intentos_fallidos(horas=1)
    fila = next((f for f in filas if f["identificador"] == "IP 10.0.0.4"), None)
    assert fila is not None
    assert fila["intentos"] == 1

    registros = await pb.list_records(
        "auditoria", {"filter": 'accion="login_fallido" && ip="10.0.0.4"', "perPage": 10}
    )
    for r in registros["items"]:
        await pb.delete_record("auditoria", r["id"])


# ── RBAC + vista ──────────────────────────────────────────────────────────

async def test_dashboard_requiere_permiso_admin(client, usuario_factory):
    pasajero = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})
    resp = await client.get("/admin/seguridad/intentos-fallidos")
    assert resp.status_code == 403


async def test_dashboard_admin_ve_intentos(admin_client, pb):
    email = "visible-en-dashboard@aerotrack.test"
    await AuditService().insertar("login_fallido", "usuarios", detalle={"email": email}, ip="10.0.0.5")

    resp = await admin_client.get("/admin/seguridad/intentos-fallidos?horas=1")
    assert resp.status_code == 200
    assert email in resp.text

    await _limpiar(pb, [email])


# ── "Expiración forzada" (desactivar cuenta) ──────────────────────────────

async def test_desactivar_cuenta_fuerza_cierre_de_sesion(client, usuario_factory, rol_administrador):
    # `client`/`admin_client` comparten el mismo httpx.AsyncClient (mismas
    # cookies) — para tener dos sesiones concurrentes de verdad (pasajero Y
    # admin al mismo tiempo) se arma un segundo cliente independiente acá,
    # en vez de pedir `admin_client` (pisaría la cookie de `client`).
    pasajero = await usuario_factory(tipo_actor="pasajero")
    resp_login = await client.post(
        "/login", data={"email": pasajero["email"], "password": pasajero["_password"]}
    )
    assert resp_login.status_code == 303
    # La sesión funciona antes de desactivar.
    assert (await client.get("/mi-perfil")).status_code == 200

    admin = await usuario_factory(tipo_actor="administrador", rol_id=rol_administrador["id"])
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as admin_http:
        resp_admin_login = await admin_http.post(
            "/login", data={"email": admin["email"], "password": admin["_password"]}
        )
        assert resp_admin_login.status_code == 303

        resp = await admin_http.post(
            "/admin/seguridad/desactivar-cuenta", data={"email": pasajero["email"], "horas": "24"}
        )
        assert resp.status_code == 303
        assert "Cuenta+desactivada" in resp.headers.get("location", "")

    # Mismo token, misma cookie -> ahora se rechaza (RN, no necesita esperar
    # a que expire el JWT, verificar_sesion revalida `activo` en vivo).
    resp_tras_desactivar = await client.get("/mi-perfil")
    assert resp_tras_desactivar.status_code in (303, 401, 403)
    assert resp_tras_desactivar.status_code != 200


async def test_desactivar_cuenta_inexistente_no_rompe(admin_client):
    resp = await admin_client.post(
        "/admin/seguridad/desactivar-cuenta",
        data={"email": "no-existe-nunca@aerotrack.test", "horas": "24"},
    )
    assert resp.status_code == 303
    assert "No+se+encontr" in resp.headers.get("location", "")


async def test_desactivar_cuenta_requiere_permiso_admin(client, usuario_factory):
    pasajero = await usuario_factory(tipo_actor="pasajero")
    otro = await usuario_factory(tipo_actor="pasajero")
    await client.post("/login", data={"email": pasajero["email"], "password": pasajero["_password"]})

    resp = await client.post(
        "/admin/seguridad/desactivar-cuenta", data={"email": otro["email"], "horas": "24"}
    )
    assert resp.status_code == 403
