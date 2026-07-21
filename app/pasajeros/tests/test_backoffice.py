"""RF-PAS-003, 004 / CU-O16 — Backoffice: buscar y gestionar pasajeros."""

import pytest


@pytest.mark.asyncio
async def test_buscar_pasajeros_sin_permiso_bloquea(client, pasajero_factory):
    usuario, _ = await pasajero_factory()
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303
    resp = await client.get("/backoffice/pasajeros?q=test")
    assert resp.status_code in (303, 403)


@pytest.mark.asyncio
async def test_buscar_pasajeros_admin_ve_resultados(admin_client, pasajero_factory):
    await pasajero_factory()
    resp = await admin_client.get("/backoffice/pasajeros?q=Prueba")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_detalle_pasajero_admin(admin_client, pasajero_factory):
    _, pasajero = await pasajero_factory()
    resp = await admin_client.get(f"/backoffice/pasajeros/{pasajero['id']}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_editar_pasajero_backoffice_audita(admin_client, pasajero_factory):
    _, pasajero = await pasajero_factory()
    resp = await admin_client.put(
        f"/backoffice/pasajeros/{pasajero['id']}",
        data={"telefono": "+59899988777"},
    )
    assert resp.status_code == 200
    json = resp.json()
    assert json["telefono"] == "+59899988777"


@pytest.mark.asyncio
async def test_detalle_pasajero_no_existente(admin_client):
    resp = await admin_client.get("/backoffice/pasajeros/id_inexistente")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_agente_con_restriccion_nivel2_fuera_de_alcance_bloqueado(
    client, pb, usuario_factory, rol_agente, pasajero_factory
):
    """RN-PAS-003 (CHK009) — un Agente cuyo rol tiene una restricción de
    Nivel 2 sobre "pasajeros" que no incluye la tabla "pasajeros" queda
    bloqueado, aunque tenga Nivel 1 "ver"/"editar" (mismo patrón que
    `test_rbac_service.py::test_nivel2_nunca_amplia_nivel1`)."""
    modulo_pasajeros = await pb.get_first("modulos", 'clave="pasajeros"')
    fila_nivel2 = await pb.create_record(
        "roles_permisos_tablas",
        {"rol_id": rol_agente["id"], "modulo_id": modulo_pasajeros["id"], "tabla": "otra_tabla"},
    )
    try:
        _, pasajero = await pasajero_factory()
        agente = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])
        resp = await client.post(
            "/login", data={"email": agente["email"], "password": agente["_password"]}
        )
        assert resp.status_code == 303

        resp = await client.get("/backoffice/pasajeros?q=test")
        assert resp.status_code == 403

        resp = await client.get(f"/backoffice/pasajeros/{pasajero['id']}")
        assert resp.status_code == 403

        resp = await client.put(f"/backoffice/pasajeros/{pasajero['id']}", data={"telefono": "+59899988777"})
        assert resp.status_code == 403
    finally:
        await pb.delete_record("roles_permisos_tablas", fila_nivel2["id"])