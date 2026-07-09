from datetime import datetime, timedelta, timezone

from app.seguridad.services.password_service import PasswordService, TokenInvalido


# ── RF-SEG-004 (CHK007) ───────────────────────────────────────────────────

async def test_mensaje_generico_para_correo_existente(client, usuario_factory):
    usuario = await usuario_factory()
    resp = await client.post("/recuperar-password", data={"email": usuario["email"]})
    assert resp.status_code == 200
    assert "Si el correo está registrado" in resp.text


async def test_mensaje_generico_para_correo_inexistente(client):
    resp = await client.post(
        "/recuperar-password", data={"email": "no-existe-nunca@aerotrack.test"}
    )
    assert resp.status_code == 200
    assert "Si el correo está registrado" in resp.text


# ── RF-SEG-005 (CHK008) ───────────────────────────────────────────────────

async def test_enlace_valido_permite_restablecer_y_login_con_nueva_password(
    client, usuario_factory
):
    usuario = await usuario_factory()
    service = PasswordService()
    token = await service.generar_token_recuperacion(usuario["id"])

    resp = await client.post(
        f"/restablecer-password/{token}",
        data={"password": "NuevaClave#456", "confirmacion": "NuevaClave#456"},
    )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/login")

    login_resp = await client.post(
        "/login", data={"email": usuario["email"], "password": "NuevaClave#456"}
    )
    assert login_resp.status_code == 303


async def test_enlace_usado_se_rechaza(client, usuario_factory):
    usuario = await usuario_factory()
    service = PasswordService()
    token = await service.generar_token_recuperacion(usuario["id"])

    await client.post(
        f"/restablecer-password/{token}",
        data={"password": "NuevaClave#456", "confirmacion": "NuevaClave#456"},
    )
    # segundo intento con el mismo token, ya consumido
    resp = await client.post(
        f"/restablecer-password/{token}",
        data={"password": "OtraClave#789", "confirmacion": "OtraClave#789"},
    )
    assert "token_invalido" not in resp.text or "expiró" in resp.text
    assert resp.status_code == 200


async def test_enlace_expirado_se_rechaza(usuario_factory, pb):
    usuario = await usuario_factory()
    service = PasswordService()
    token = await service.generar_token_recuperacion(usuario["id"])
    # forzar expiración en el pasado directamente en PocketBase
    expirado = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    await pb.update_record("usuarios", usuario["id"], {"reset_token_expira": expirado})

    try:
        await service.validar_token(token)
        assert False, "debía lanzar TokenInvalido"
    except TokenInvalido:
        pass


async def test_contraseñas_no_coinciden_rechaza(client, usuario_factory):
    usuario = await usuario_factory()
    service = PasswordService()
    token = await service.generar_token_recuperacion(usuario["id"])

    resp = await client.post(
        f"/restablecer-password/{token}",
        data={"password": "NuevaClave#456", "confirmacion": "OtraCosa#789"},
    )
    assert resp.status_code == 400
    assert "no coinciden" in resp.text


# ── RNF-SEG-004 (CHK026, CHK037) ──────────────────────────────────────────

async def test_expiracion_lee_configuracion_ya_sembrada():
    service = PasswordService()
    minutos = await service.minutos_expiracion_recuperacion()
    assert minutos == 30  # sembrado por bootstrap_configuracion_sistema.py


async def test_expiracion_fallback_si_no_hay_clave(monkeypatch):
    service = PasswordService()

    async def get_config_none(clave):
        return None

    monkeypatch.setattr(service._repo, "get_config", get_config_none)
    minutos = await service.minutos_expiracion_recuperacion()
    assert minutos == 30  # DEFAULT_EXPIRACION_MINUTOS documentado en código
