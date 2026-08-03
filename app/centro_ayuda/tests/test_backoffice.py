"""CU-T28 (artículos, Administrador), CU-T29 (métricas, Administrador),
CU-T36 (casos escalados, Agente) — incluye el RBAC Nivel 2 que restringe
a Agente a la tabla `casos_escalados` (sembrado en
`scripts/seed_centro_ayuda_rbac.py`)."""

from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.shared import minio_operational_client as moc


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


async def test_admin_puede_editar_articulo_sin_tocar_estado(pb, admin_client):
    """WP-05 (auditoría de WorkPanels, 2026-07-31) — Editar ya no archiva
    como efecto secundario de omitir un checkbox; es una acción aparte
    (test_admin_puede_archivar_articulo, abajo)."""
    articulo = await pb.create_record(
        "articulos_ayuda",
        {
            "categoria": "Test", "titulo": "Para editar", "contenido": "x",
            "autor_id": admin_client.admin_usuario["id"], "activo": True,
            "fecha_publicacion": "2027-01-01 00:00:00.000Z",
        },
    )

    resp = await admin_client.post(
        f"/backoffice/ayuda/articulos/{articulo['id']}",
        data={"categoria": "Test", "titulo": "Título editado", "contenido": "y"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    actualizado = await pb.get_record("articulos_ayuda", articulo["id"])
    assert actualizado["titulo"] == "Título editado"
    assert actualizado["activo"] is True

    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_admin_puede_archivar_y_reactivar_articulo(pb, admin_client):
    articulo = await pb.create_record(
        "articulos_ayuda",
        {
            "categoria": "Test", "titulo": "Para archivar", "contenido": "x",
            "autor_id": admin_client.admin_usuario["id"], "activo": True,
            "fecha_publicacion": "2027-01-01 00:00:00.000Z",
        },
    )

    resp = await admin_client.post(
        f"/backoffice/ayuda/articulos/{articulo['id']}/archivar", follow_redirects=True
    )
    assert resp.status_code == 200
    assert "archivado" in resp.text.lower()
    actualizado = await pb.get_record("articulos_ayuda", articulo["id"])
    assert actualizado["activo"] is False

    resp = await admin_client.post(
        f"/backoffice/ayuda/articulos/{articulo['id']}/archivar", follow_redirects=True
    )
    assert resp.status_code == 200
    assert "reactivado" in resp.text.lower()
    actualizado = await pb.get_record("articulos_ayuda", articulo["id"])
    assert actualizado["activo"] is True

    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_filtros_articulos_backoffice(pb, admin_client):
    articulo = await pb.create_record(
        "articulos_ayuda",
        {
            "categoria": "Categoria Filtro Unica", "titulo": "Titulo Filtro Unico", "contenido": "x",
            "autor_id": admin_client.admin_usuario["id"], "activo": True,
            "fecha_publicacion": "2027-01-01 00:00:00.000Z",
        },
    )
    try:
        resp = await admin_client.get(
            "/backoffice/ayuda/articulos", params={"categoria": "Categoria Filtro Unica"}
        )
        assert resp.status_code == 200
        assert "Titulo Filtro Unico" in resp.text

        resp = await admin_client.get("/backoffice/ayuda/articulos", params={"texto": "Filtro Unico"})
        assert resp.status_code == 200
        assert "Titulo Filtro Unico" in resp.text

        resp = await admin_client.get("/backoffice/ayuda/articulos", params={"estado": "archivado"})
        assert resp.status_code == 200
        assert "Titulo Filtro Unico" not in resp.text  # está activo, no debe aparecer en "archivado"
    finally:
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


async def test_agente_puede_resolver_caso(agente_client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    repo = CentroAyudaRepository()
    caso = await repo.crear_caso(
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso de prueba", "mensaje": "x",
            "estado": "abierto", "fecha_creacion": "2027-01-01 00:00:00.000Z",
        },
    )

    resp = await agente_client.post(f"/backoffice/ayuda/casos/{caso['id']}/resolver", follow_redirects=True)
    assert resp.status_code == 200

    actualizado = await repo.obtener_caso(caso["id"])
    assert actualizado["estado"] == "resuelto"
    assert actualizado["fecha_resolucion"]
    assert actualizado["agente_asignado_id"] == agente_client.agente_usuario["id"]

    await moc.eliminar("casos_escalados", caso["id"])


async def test_admin_puede_ver_metricas_con_datos_reales(pb, admin_client):
    articulo = await pb.create_record(
        "articulos_ayuda",
        {
            "categoria": "Test", "titulo": "Artículo con calificaciones", "contenido": "x",
            "autor_id": admin_client.admin_usuario["id"], "activo": True,
            "fecha_publicacion": "2027-01-01 00:00:00.000Z",
        },
    )
    calificacion = await CentroAyudaRepository().crear_calificacion(
        articulo["id"], None, "arriba", "2027-01-01 00:00:00.000Z"
    )

    resp = await admin_client.get("/backoffice/ayuda/metricas")
    assert resp.status_code == 200
    assert "Artículo con calificaciones" in resp.text

    await moc.eliminar("articulo_calificaciones", calificacion["id"])
    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_listar_casos_filtra_por_estado(agente_client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    repo = CentroAyudaRepository()
    abierto = await repo.crear_caso(
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso abierto filtro", "mensaje": "x",
            "estado": "abierto", "fecha_creacion": "2027-01-01 00:00:00.000Z",
        },
    )
    resuelto = await repo.crear_caso(
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso resuelto filtro", "mensaje": "x",
            "estado": "resuelto", "fecha_creacion": "2027-01-01 00:00:00.000Z", "fecha_resolucion": "2027-01-02 00:00:00.000Z",
        },
    )

    resp = await agente_client.get("/backoffice/ayuda/casos", params={"estado": "abierto"})
    assert resp.status_code == 200
    assert "Caso abierto filtro" in resp.text
    assert "Caso resuelto filtro" not in resp.text

    await moc.eliminar("casos_escalados", abierto["id"])
    await moc.eliminar("casos_escalados", resuelto["id"])


# ── WP-11 (auditoría de WorkPanels, 2026-07-31) ──────────────────────────

async def test_ver_detalle_caso_muestra_contacto_y_confirmacion_antes_de_resolver(
    agente_client, pasajero_factory
):
    usuario, pasajero = await pasajero_factory()
    repo = CentroAyudaRepository()
    caso = await repo.crear_caso(
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso con detalle WP11", "mensaje": "Mensaje completo de prueba",
            "estado": "abierto", "fecha_creacion": "2027-01-01 00:00:00.000Z",
        },
    )
    try:
        resp = await agente_client.get("/backoffice/ayuda/casos")
        assert resp.status_code == 200
        assert "Caso con detalle WP11" in resp.text
        assert usuario["email"] in resp.text  # datos de contacto en el modal de detalle
        assert "Marcar resuelto" in resp.text  # botón que abre el modal de confirmación, no submit directo
    finally:
        await moc.eliminar("casos_escalados", caso["id"])


# ── IS-13 (auditoría de informes simples, 2026-08-01) — filtro de período,
# antigüedad ("días abierto") y exportar CSV ─────────────────────────────

async def test_casos_filtro_periodo(agente_client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    repo = CentroAyudaRepository()
    viejo = await repo.crear_caso(
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso viejo periodo", "mensaje": "x",
            "estado": "abierto", "fecha_creacion": "2020-01-01 00:00:00.000Z",
        },
    )
    reciente = await repo.crear_caso(
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso reciente periodo", "mensaje": "x",
            "estado": "abierto", "fecha_creacion": "2027-01-01 00:00:00.000Z",
        },
    )
    try:
        resp = await agente_client.get("/backoffice/ayuda/casos", params={"desde": "2025-01-01"})
        assert resp.status_code == 200
        assert "Caso reciente periodo" in resp.text
        assert "Caso viejo periodo" not in resp.text
    finally:
        await moc.eliminar("casos_escalados", viejo["id"])
        await moc.eliminar("casos_escalados", reciente["id"])


async def test_casos_muestra_dias_abierto(agente_client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    repo = CentroAyudaRepository()
    caso = await repo.crear_caso(
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso antiguedad", "mensaje": "x",
            "estado": "abierto", "fecha_creacion": "2020-01-01 00:00:00.000Z",
        },
    )
    try:
        resp = await agente_client.get("/backoffice/ayuda/casos")
        assert resp.status_code == 200
        assert "días abierto" in resp.text
    finally:
        await moc.eliminar("casos_escalados", caso["id"])


async def test_exportar_casos_csv(agente_client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    repo = CentroAyudaRepository()
    caso = await repo.crear_caso(
        {
            "pasajero_id": pasajero["id"], "asunto": "Caso export csv", "mensaje": "x",
            "estado": "abierto", "fecha_creacion": "2027-01-01 00:00:00.000Z",
        },
    )
    try:
        resp = await agente_client.get("/backoffice/ayuda/casos/exportar")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert resp.text.splitlines()[0] == "fecha_creacion,asunto,pasajero,estado,dias_abierto,agente"
        assert "Caso export csv" in resp.text
    finally:
        await moc.eliminar("casos_escalados", caso["id"])
