"""RF-PAS-002 / CU-O15 — Editar datos de contacto."""

import pytest

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository


@pytest.mark.asyncio
async def test_contacto_telefono_valido_se_actualiza(pasajero_client, pb):
    resp = await pasajero_client.post(
        "/mi-perfil/contacto",
        data={"telefono": "+59899123456"},
    )
    assert resp.status_code == 303
    assert "Contacto+actualizado" in resp.headers.get("location", "")

    actualizado = await PasajerosRepository().obtener_pasajero(pasajero_client.pasajero["id"])
    assert actualizado["telefono"] == "+59899123456"

    registro = await pb.get_first(
        "auditoria",
        f'accion="editar" && tabla="pasajeros" && registro_id="{pasajero_client.pasajero["id"]}"',
    )
    assert registro is not None
    assert registro["usuario_id"] == pasajero_client.pasajero_usuario["id"]
    assert registro["detalle"]["origen"] == "autoservicio"
    await pb.delete_record("auditoria", registro["id"])


@pytest.mark.asyncio
async def test_contacto_no_permite_cambiar_correo(pasajero_client, pb):
    """RF-PAS-002 — el correo no es editable desde este formulario (fuera de
    alcance): aunque se envíe `email` en el POST, el router no lo declara
    como parámetro y PocketBase nunca lo recibe."""
    resp = await pasajero_client.post(
        "/mi-perfil/contacto",
        data={"telefono": "+59899123456", "email": "otro@aerotrack.test"},
    )
    assert resp.status_code == 303

    usuario_sin_cambios = await pb.get_record("usuarios", pasajero_client.pasajero_usuario["id"])
    assert usuario_sin_cambios["email"] == pasajero_client.pasajero_usuario["email"]

    registro = await pb.get_first(
        "auditoria",
        f'accion="editar" && tabla="pasajeros" && registro_id="{pasajero_client.pasajero["id"]}"',
    )
    if registro is not None:
        await pb.delete_record("auditoria", registro["id"])


@pytest.mark.asyncio
async def test_contacto_telefono_invalido_rechazado(pasajero_client):
    resp = await pasajero_client.post(
        "/mi-perfil/contacto",
        data={"telefono": "abc"},
    )
    assert resp.status_code == 303
    # Starlette codifica el Location header (espacios -> %20, tildes ->
    # UTF-8 percent-encoded) — se compara contra un fragmento ASCII plano
    # del mensaje real, no contra el texto con tildes sin decodificar.
    assert "formato" in resp.headers.get("location", "")


@pytest.mark.asyncio
async def test_contacto_sin_sesion_redirige(client):
    resp = await client.post("/mi-perfil/contacto", data={"telefono": "+59899123456"})
    assert resp.status_code == 303
    assert "/login" in resp.headers.get("location", "")