"""RF-PAS-003, 004 / CU-O16 — Backoffice: buscar y gestionar pasajeros."""

import uuid

import pytest

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository


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
    `test_rbac_service.py::test_nivel2_nunca_amplia_nivel1`).

    Nivel 2 restringe por (tabla, accion) desde 2026-07-30 — se necesita
    una fila por cada acción que se quiere bloquear, "ver" y "editar", para
    reproducir el bloqueo total que antes daba una sola fila sin accion."""
    modulo_pasajeros = await pb.get_first("modulos", 'clave="pasajeros"')
    filas_nivel2 = [
        await pb.create_record(
            "roles_permisos_tablas",
            {"rol_id": rol_agente["id"], "modulo_id": modulo_pasajeros["id"], "tabla": "otra_tabla", "accion": accion},
        )
        for accion in ("ver", "editar")
    ]
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
        for fila in filas_nivel2:
            await pb.delete_record("roles_permisos_tablas", fila["id"])


# ── WP-01 (auditoría de WorkPanels, 2026-07-31) — CRUD completo ──────────

def _datos_pasajero_nuevo(**overrides) -> dict:
    email = f"wp01-{uuid.uuid4().hex[:10]}@aerotrack.test"
    data = {
        "nombre_completo": "Pasajero De Prueba WP01",
        "email": email,
        "password": "ClaveSegura2026",
        "fecha_nacimiento": "1992-05-14",
        "telefono": "+593991234567",
        "numero_documento": f"DOC{uuid.uuid4().hex[:6].upper()}",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_crear_pasajero_backoffice(admin_client, pb):
    datos = _datos_pasajero_nuevo()
    resp = await admin_client.post("/backoffice/pasajeros", data=datos, follow_redirects=True)
    assert resp.status_code == 200
    assert "Pasajero creado" in resp.text

    usuario = await pb.get_first("usuarios", f'email="{datos["email"]}"')
    assert usuario is not None
    pasajero = await PasajerosRepository().pasajero_de_usuario(usuario["id"])
    assert pasajero is not None
    assert pasajero["numero_documento"] == datos["numero_documento"]
    assert pasajero["canal_registro"] == "agente_call_center"

    await PasajerosRepository().eliminar_pasajero(pasajero["id"])
    await pb.delete_record("usuarios", usuario["id"])


@pytest.mark.asyncio
async def test_crear_pasajero_backoffice_correo_duplicado(admin_client, pasajero_factory):
    usuario_existente, _ = await pasajero_factory()
    datos = _datos_pasajero_nuevo(email=usuario_existente["email"])
    resp = await admin_client.post("/backoffice/pasajeros", data=datos, follow_redirects=True)
    assert resp.status_code == 200
    assert "correo" in resp.text.lower()


@pytest.mark.asyncio
async def test_editar_pasajero_backoffice_completo(admin_client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    nuevo_email = f"wp01-editado-{uuid.uuid4().hex[:8]}@aerotrack.test"
    resp = await admin_client.post(
        f"/backoffice/pasajeros/{pasajero['id']}/editar",
        data={
            "nombre_completo": "Nombre Editado WP01",
            "email": nuevo_email,
            "telefono": "+593987654321",
            "numero_documento": "DOCEDITADO01",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Pasajero actualizado" in resp.text

    usuario_actualizado = await pb.get_record("usuarios", usuario["id"])
    assert usuario_actualizado["nombre_completo"] == "Nombre Editado WP01"
    assert usuario_actualizado["email"] == nuevo_email
    pasajero_actualizado = await PasajerosRepository().obtener_pasajero(pasajero["id"])
    assert pasajero_actualizado["telefono"] == "+593987654321"
    assert pasajero_actualizado["numero_documento"] == "DOCEDITADO01"


@pytest.mark.asyncio
async def test_editar_pasajero_backoffice_fecha_nacimiento_vacia_no_falla(admin_client, pasajero_factory):
    """`fecha_nacimiento` llega como string vacío (no ausente) cuando el
    admin limpia el campo en el form — un input HTML de tipo date siempre
    manda el nombre del campo, con value="" si está vacío. Antes el
    parámetro era `date | None = Form(None)` directo, y FastAPI intentaba
    coercionar "" a date ANTES de que el body pudiera normalizarlo a None
    (mismo patrón que el resto de los campos), tirando 422."""
    _usuario, pasajero = await pasajero_factory()
    resp = await admin_client.post(
        f"/backoffice/pasajeros/{pasajero['id']}/editar",
        data={"nombre_completo": "Nombre Sin Fecha", "fecha_nacimiento": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Pasajero actualizado" in resp.text


@pytest.mark.asyncio
async def test_editar_pasajero_backoffice_correo_duplicado(admin_client, pasajero_factory):
    _, pasajero_a = await pasajero_factory()
    usuario_b, _ = await pasajero_factory()
    resp = await admin_client.post(
        f"/backoffice/pasajeros/{pasajero_a['id']}/editar",
        data={"email": usuario_b["email"]},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "correo" in resp.text.lower()


@pytest.mark.asyncio
async def test_eliminar_pasajero_backoffice_sin_reservas(admin_client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    resp = await admin_client.post(f"/backoffice/pasajeros/{pasajero['id']}/eliminar", follow_redirects=True)
    assert resp.status_code == 200
    assert "Pasajero eliminado" in resp.text

    assert await PasajerosRepository().obtener_pasajero(pasajero["id"]) is None
    usuario_actualizado = await pb.get_record("usuarios", usuario["id"])
    assert usuario_actualizado["activo"] is False


@pytest.mark.asyncio
async def test_eliminar_pasajero_backoffice_bloqueado_con_reserva_activa(
    admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    _, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada")

    resp = await admin_client.post(f"/backoffice/pasajeros/{pasajero['id']}/eliminar", follow_redirects=True)
    assert resp.status_code == 200
    assert "reserva" in resp.text.lower()

    assert await PasajerosRepository().obtener_pasajero(pasajero["id"]) is not None


@pytest.mark.asyncio
async def test_documento_viaje_crear_y_eliminar_backoffice(admin_client, pasajero_factory):
    _, pasajero = await pasajero_factory()
    resp = await admin_client.post(
        f"/backoffice/pasajeros/{pasajero['id']}/documentos",
        data={"tipo": "pasaporte", "numero": "P1234567", "pais_emision": "EC"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Documento agregado" in resp.text

    documentos = await PasajerosRepository().documentos_de_pasajero(pasajero["id"])
    assert len(documentos) == 1
    assert documentos[0]["numero"] == "P1234567"

    resp = await admin_client.post(
        f"/backoffice/pasajeros/{pasajero['id']}/documentos/{documentos[0]['id']}/eliminar",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Documento eliminado" in resp.text
    assert await PasajerosRepository().documentos_de_pasajero(pasajero["id"]) == []


@pytest.mark.asyncio
async def test_filtros_busqueda_pasajeros_backoffice(admin_client, pasajero_factory):
    usuario, pasajero = await pasajero_factory(nombre_completo="Zoraida Filtro Unico")

    resp = await admin_client.get("/backoffice/pasajeros", params={"nombre": "Zoraida Filtro"})
    assert resp.status_code == 200
    assert "Zoraida Filtro Unico" in resp.text

    resp = await admin_client.get("/backoffice/pasajeros", params={"email": usuario["email"]})
    assert resp.status_code == 200
    assert "Zoraida Filtro Unico" in resp.text

    resp = await admin_client.get("/backoffice/pasajeros", params={"nombre": "Nombre Que No Existe Nunca"})
    assert resp.status_code == 200
    assert "Sin resultados" in resp.text