"""CU-T28 (artículos, Administrador), CU-T29 (métricas, Administrador),
CU-T36 (casos escalados, Agente) — incluye el RBAC Nivel 2 que restringe
a Agente a la tabla `casos_escalados` (sembrado en
`scripts/seed_centro_ayuda_rbac.py`)."""


async def test_admin_puede_crear_articulo(pb, admin_client):
    resp = await admin_client.post(
        "/backoffice/ayuda/articulos",
        data={"categoria": "Reservas", "titulo": "Artículo de prueba backoffice", "contenido": "Contenido real"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Artículo de prueba backoffice" in resp.text

    creados = await pb.list_records("articulos_ayuda", {"filter": 'titulo="Artículo de prueba backoffice"'})
    assert creados["totalItems"] == 1
    for a in creados["items"]:
        await pb.delete_record("articulos_ayuda", a["id"])


async def test_admin_puede_archivar_articulo(pb, admin_client):
    articulo = await pb.create_record(
        "articulos_ayuda",
        {
            "categoria": "Test", "titulo": "Para archivar", "contenido": "x",
            "autor_id": admin_client.admin_usuario["id"], "activo": True,
            "fecha_publicacion": "2027-01-01 00:00:00.000Z",
        },
    )

    resp = await admin_client.post(
        f"/backoffice/ayuda/articulos/{articulo['id']}",
        data={"categoria": "Test", "titulo": "Para archivar", "contenido": "x"},  # sin 'activo' = false
        follow_redirects=True,
    )
    assert resp.status_code == 200

    actualizado = await pb.get_record("articulos_ayuda", articulo["id"])
    assert actualizado["activo"] is False

    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_agente_no_puede_gestionar_articulos(agente_client):
    resp = await agente_client.get("/backoffice/ayuda/articulos")
    assert resp.status_code == 403


async def test_agente_no_puede_ver_metricas(agente_client):
    resp = await agente_client.get("/backoffice/ayuda/metricas")
    assert resp.status_code == 403


async def test_agente_puede_ver_casos(agente_client):
    resp = await agente_client.get("/backoffice/ayuda/casos")
    assert resp.status_code == 200


async def test_agente_puede_resolver_caso(pb, agente_client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    caso = await pb.create_record(
        "casos_escalados",
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso de prueba", "mensaje": "x",
            "estado": "abierto", "fecha_creacion": "2027-01-01 00:00:00.000Z",
        },
    )

    resp = await agente_client.post(f"/backoffice/ayuda/casos/{caso['id']}/resolver", follow_redirects=True)
    assert resp.status_code == 200

    actualizado = await pb.get_record("casos_escalados", caso["id"])
    assert actualizado["estado"] == "resuelto"
    assert actualizado["fecha_resolucion"]
    assert actualizado["agente_asignado_id"] == agente_client.agente_usuario["id"]

    await pb.delete_record("casos_escalados", caso["id"])


async def test_admin_puede_ver_metricas_con_datos_reales(pb, admin_client):
    articulo = await pb.create_record(
        "articulos_ayuda",
        {
            "categoria": "Test", "titulo": "Artículo con calificaciones", "contenido": "x",
            "autor_id": admin_client.admin_usuario["id"], "activo": True,
            "fecha_publicacion": "2027-01-01 00:00:00.000Z",
        },
    )
    calificacion = await pb.create_record(
        "articulo_calificaciones", {"articulo_id": articulo["id"], "util": "arriba", "fecha": "2027-01-01 00:00:00.000Z"}
    )

    resp = await admin_client.get("/backoffice/ayuda/metricas")
    assert resp.status_code == 200
    assert "Artículo con calificaciones" in resp.text

    await pb.delete_record("articulo_calificaciones", calificacion["id"])
    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_listar_casos_filtra_por_estado(pb, agente_client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    abierto = await pb.create_record(
        "casos_escalados",
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso abierto filtro", "mensaje": "x",
            "estado": "abierto", "fecha_creacion": "2027-01-01 00:00:00.000Z",
        },
    )
    resuelto = await pb.create_record(
        "casos_escalados",
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso resuelto filtro", "mensaje": "x",
            "estado": "resuelto", "fecha_creacion": "2027-01-01 00:00:00.000Z", "fecha_resolucion": "2027-01-02 00:00:00.000Z",
        },
    )

    resp = await agente_client.get("/backoffice/ayuda/casos", params={"estado": "abierto"})
    assert resp.status_code == 200
    assert "Caso abierto filtro" in resp.text
    assert "Caso resuelto filtro" not in resp.text

    await pb.delete_record("casos_escalados", abierto["id"])
    await pb.delete_record("casos_escalados", resuelto["id"])
