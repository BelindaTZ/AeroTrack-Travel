"""RF-PAS-005 (CU-O49) — documentos de viaje, autoservicio."""

import pytest

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository


@pytest.mark.asyncio
async def test_agregar_documento_de_viaje(pasajero_client, pb):
    resp = await pasajero_client.post(
        "/mi-perfil/documentos",
        data={"tipo": "pasaporte", "numero": "AB123456", "pais_emision": "Ecuador", "fecha_vencimiento": "2030-01-01"},
    )
    assert resp.status_code == 303
    assert "Documento+agregado" in resp.headers.get("location", "")

    repo = PasajerosRepository()
    documentos = await repo.documentos_de_pasajero(pasajero_client.pasajero["id"])
    assert len(documentos) == 1
    documento = documentos[0]
    assert documento["numero"] == "AB123456"
    assert documento["pais_emision"] == "Ecuador"
    await repo.eliminar_documento(documento["id"])


@pytest.mark.asyncio
async def test_agregar_documento_tipo_invalido_rechaza(pasajero_client, pb):
    resp = await pasajero_client.post(
        "/mi-perfil/documentos",
        data={"tipo": "licencia_de_conducir", "numero": "X1", "pais_emision": "Ecuador"},
    )
    assert resp.status_code == 303
    assert "no" in resp.headers.get("location", "").lower()

    repo = PasajerosRepository()
    documentos = await repo.documentos_de_pasajero(pasajero_client.pasajero["id"])
    assert documentos == []


@pytest.mark.asyncio
async def test_eliminar_documento_propio(pasajero_client, pb):
    repo = PasajerosRepository()
    documento = await repo.crear_documento(
        {
            "pasajero_id": pasajero_client.pasajero["id"], "tipo": "cedula",
            "numero": "0999999999", "pais_emision": "Ecuador",
        },
    )
    resp = await pasajero_client.post(f"/mi-perfil/documentos/{documento['id']}/eliminar")
    assert resp.status_code == 303
    assert "Documento+eliminado" in resp.headers.get("location", "")

    borrado = await repo.obtener_documento(documento["id"])
    assert borrado is None


@pytest.mark.asyncio
async def test_eliminar_documento_ajeno_no_permite(pasajero_client, pasajero_factory, pb):
    _otro_usuario, otro_pasajero = await pasajero_factory()
    repo = PasajerosRepository()
    documento_ajeno = await repo.crear_documento(
        {
            "pasajero_id": otro_pasajero["id"], "tipo": "pasaporte",
            "numero": "ZZ000000", "pais_emision": "Ecuador",
        },
    )

    resp = await pasajero_client.post(f"/mi-perfil/documentos/{documento_ajeno['id']}/eliminar")
    assert resp.status_code == 303
    assert "No+se+pudo" in resp.headers.get("location", "")

    sigue_existiendo = await repo.obtener_documento(documento_ajeno["id"])
    assert sigue_existiendo is not None
    await repo.eliminar_documento(documento_ajeno["id"])


@pytest.mark.asyncio
async def test_mi_perfil_lista_documentos_propios(pasajero_client, pb):
    repo = PasajerosRepository()
    documento = await repo.crear_documento(
        {
            "pasajero_id": pasajero_client.pasajero["id"], "tipo": "pasaporte",
            "numero": "PP778899", "pais_emision": "Perú",
        },
    )
    resp = await pasajero_client.get("/mi-perfil")
    assert resp.status_code == 200
    assert "PP778899" in resp.text
    assert "Perú" in resp.text
    await repo.eliminar_documento(documento["id"])


@pytest.mark.asyncio
async def test_direccion_de_facturacion_se_persiste(pasajero_client, pb):
    """Regresión: `actualizar_contacto` escribía en un campo "direccion" que
    no existe en el esquema (real: direccion_facturacion) — PocketBase lo
    descartaba en silencio y la dirección nunca se guardaba."""
    resp = await pasajero_client.post(
        "/mi-perfil/contacto",
        data={"telefono": "+59899123456", "direccion": "Av. Siempre Viva 742"},
    )
    assert resp.status_code == 303

    actualizado = await PasajerosRepository().obtener_pasajero(pasajero_client.pasajero["id"])
    assert actualizado["direccion_facturacion"] == "Av. Siempre Viva 742"

    registro = await pb.get_first(
        "auditoria",
        f'accion="editar" && tabla="pasajeros" && registro_id="{pasajero_client.pasajero["id"]}"',
    )
    if registro is not None:
        await pb.delete_record("auditoria", registro["id"])
