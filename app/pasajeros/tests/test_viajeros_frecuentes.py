"""RF-PAS-006 (CU-O50) — viajeros frecuentes, autoservicio."""

import pytest

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository


@pytest.mark.asyncio
async def test_agregar_viajero_frecuente(pasajero_client, pb):
    resp = await pasajero_client.post(
        "/mi-perfil/viajeros-frecuentes",
        data={"nombre_completo": "Juan Pérez", "relacion": "Hijo", "fecha_nacimiento": "2015-05-20"},
    )
    assert resp.status_code == 303
    assert "Viajero+frecuente+agregado" in resp.headers.get("location", "")

    repo = PasajerosRepository()
    viajeros = await repo.viajeros_frecuentes_de_pasajero(pasajero_client.pasajero["id"])
    assert len(viajeros) == 1
    viajero = viajeros[0]
    assert viajero["nombre_completo"] == "Juan Pérez"
    assert viajero["relacion"] == "Hijo"
    await repo.eliminar_viajero_frecuente(viajero["id"])


@pytest.mark.asyncio
async def test_eliminar_viajero_frecuente_propio(pasajero_client, pb):
    repo = PasajerosRepository()
    viajero = await repo.crear_viajero_frecuente(
        {"pasajero_id": pasajero_client.pasajero["id"], "nombre_completo": "Ana Gómez"},
    )
    resp = await pasajero_client.post(f"/mi-perfil/viajeros-frecuentes/{viajero['id']}/eliminar")
    assert resp.status_code == 303

    borrado = await repo.obtener_viajero_frecuente(viajero["id"])
    assert borrado is None


@pytest.mark.asyncio
async def test_eliminar_viajero_frecuente_ajeno_no_permite(pasajero_client, pasajero_factory, pb):
    _otro_usuario, otro_pasajero = await pasajero_factory()
    repo = PasajerosRepository()
    viajero_ajeno = await repo.crear_viajero_frecuente(
        {"pasajero_id": otro_pasajero["id"], "nombre_completo": "Carlos Ruiz"},
    )

    resp = await pasajero_client.post(f"/mi-perfil/viajeros-frecuentes/{viajero_ajeno['id']}/eliminar")
    assert resp.status_code == 303
    assert "No+se+pudo" in resp.headers.get("location", "")

    sigue_existiendo = await repo.obtener_viajero_frecuente(viajero_ajeno["id"])
    assert sigue_existiendo is not None
    await repo.eliminar_viajero_frecuente(viajero_ajeno["id"])


@pytest.mark.asyncio
async def test_mi_perfil_lista_viajeros_frecuentes_propios(pasajero_client, pb):
    repo = PasajerosRepository()
    viajero = await repo.crear_viajero_frecuente(
        {"pasajero_id": pasajero_client.pasajero["id"], "nombre_completo": "María López"},
    )
    resp = await pasajero_client.get("/mi-perfil")
    assert resp.status_code == 200
    assert "María López" in resp.text
    await repo.eliminar_viajero_frecuente(viajero["id"])
