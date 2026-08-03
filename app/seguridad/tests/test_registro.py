import uuid

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.shared import minio_operational_client as moc


def _datos_validos(**overrides) -> dict:
    data = {
        "nombre_completo": "Pasajero de Prueba",
        "email": f"registro.{uuid.uuid4().hex[:10]}@aerotrack.test",
        "fecha_nacimiento": "1995-05-20",
        "telefono": "0999999999",
        "password": "ClaveSegura#123",
        "confirmacion": "ClaveSegura#123",
    }
    data.update(overrides)
    return data


async def _limpiar(pb, email: str) -> None:
    usuario = await pb.get_first("usuarios", f'email="{email}"')
    if usuario is None:
        return
    pasajero = await PasajerosRepository().pasajero_de_usuario(usuario["id"])
    if pasajero:
        await moc.eliminar("pasajeros", pasajero["id"])
        try:
            await pb.delete_record("pasajeros", pasajero["id"])  # limpia el espejo, ver RC-OP-003
        except Exception:
            pass
    await pb.delete_record("usuarios", usuario["id"])


# ── RF-SEG-008 (CHK011) ───────────────────────────────────────────────────

async def test_registro_exitoso_crea_cuenta_y_permite_login(client, pb):
    datos = _datos_validos()
    resp = await client.post("/registro", data=datos)
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/login")

    login_resp = await client.post(
        "/login", data={"email": datos["email"], "password": datos["password"]}
    )
    assert login_resp.status_code == 303

    usuario = await pb.get_first("usuarios", f'email="{datos["email"]}"')
    assert usuario is not None
    rol = await pb.get_record("roles", usuario["rol_id"])
    assert rol["nombre"] == "Pasajero"
    pasajero = await PasajerosRepository().pasajero_de_usuario(usuario["id"])
    assert pasajero is not None
    assert pasajero["telefono"] == datos["telefono"]

    await _limpiar(pb, datos["email"])


async def test_registro_correo_duplicado_rechaza(client, pb, usuario_factory):
    existente = await usuario_factory()
    datos = _datos_validos(email=existente["email"])
    resp = await client.post("/registro", data=datos)
    assert resp.status_code == 409
    assert "ya está registrado" in resp.text


async def test_registro_contraseñas_no_coinciden_rechaza(client):
    datos = _datos_validos(confirmacion="OtraClave#999")
    resp = await client.post("/registro", data=datos)
    assert resp.status_code == 400
    assert "no coinciden" in resp.text


# ── RNF-SEG-005 (CHK012) ──────────────────────────────────────────────────

def test_formulario_de_registro_no_tiene_campo_de_archivo():
    with open("app/seguridad/templates/registro.html", encoding="utf-8") as f:
        html = f.read()
    assert 'type="file"' not in html
