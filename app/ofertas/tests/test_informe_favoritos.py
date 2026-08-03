"""IS-23 (auditoría de informes simples, sesión 2026-08-01) — filtro por
tipo, período (sobre `fecha_guardado`), paginación y exportar CSV sobre el
ranking de favoritos (CU-T55), ya existente y ya ordenado por conteo
descendente."""

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.shared import minio_operational_client as moc


async def test_filtro_por_tipo(admin_client, pasajero_factory):
    _usuario, pasajero = await pasajero_factory()
    repo = CuentaRepository()
    fav_hotel = await repo.crear_favorito(pasajero["id"], "hotel", "hotel-informe-test", "2027-01-01 00:00:00.000Z")
    fav_auto = await repo.crear_favorito(pasajero["id"], "auto", "auto-informe-test", "2027-01-01 00:00:00.000Z")

    try:
        resp = await admin_client.get("/backoffice/ofertas/reporte-favoritos?tipo=hotel")
        assert resp.status_code == 200
        assert "hotel-informe-test" in resp.text
        assert "auto-informe-test" not in resp.text
    finally:
        await moc.eliminar("favoritos", fav_hotel["id"])
        await moc.eliminar("favoritos", fav_auto["id"])


async def test_filtro_por_periodo(admin_client, pasajero_factory):
    _usuario, pasajero = await pasajero_factory()
    repo = CuentaRepository()
    viejo = await repo.crear_favorito(pasajero["id"], "crucero", "crucero-viejo-test", "2020-01-01 00:00:00.000Z")
    reciente = await repo.crear_favorito(pasajero["id"], "crucero", "crucero-reciente-test", "2027-01-01 00:00:00.000Z")

    try:
        resp = await admin_client.get("/backoffice/ofertas/reporte-favoritos?desde=2025-01-01")
        assert resp.status_code == 200
        assert "crucero-reciente-test" in resp.text
        assert "crucero-viejo-test" not in resp.text
    finally:
        await moc.eliminar("favoritos", viejo["id"])
        await moc.eliminar("favoritos", reciente["id"])


async def test_ranking_ordenado_descendente_por_conteo(admin_client, pasajero_factory):
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()
    repo = CuentaRepository()
    # "producto-popular-test" guardado 2 veces, "producto-solo-test" 1 vez
    fav_1 = await repo.crear_favorito(pasajero_a["id"], "actividad", "producto-popular-test", "2027-01-01 00:00:00.000Z")
    fav_2 = await repo.crear_favorito(pasajero_b["id"], "actividad", "producto-popular-test", "2027-01-01 00:00:00.000Z")
    fav_3 = await repo.crear_favorito(pasajero_a["id"], "actividad", "producto-solo-test", "2027-01-01 00:00:00.000Z")

    try:
        resp = await admin_client.get("/backoffice/ofertas/reporte-favoritos?tipo=actividad")
        assert resp.status_code == 200
        pos_popular = resp.text.find("producto-popular-test")
        pos_solo = resp.text.find("producto-solo-test")
        assert pos_popular != -1 and pos_solo != -1
        assert pos_popular < pos_solo  # el más guardado aparece primero
    finally:
        await moc.eliminar("favoritos", fav_1["id"])
        await moc.eliminar("favoritos", fav_2["id"])
        await moc.eliminar("favoritos", fav_3["id"])


async def test_paginacion(admin_client):
    resp = await admin_client.get("/backoffice/ofertas/reporte-favoritos?page=1")
    assert resp.status_code == 200

    resp = await admin_client.get("/backoffice/ofertas/reporte-favoritos?page=999")
    assert resp.status_code == 200


async def test_exportar_csv(admin_client, pasajero_factory):
    _usuario, pasajero = await pasajero_factory()
    repo = CuentaRepository()
    fav = await repo.crear_favorito(pasajero["id"], "paquete", "paquete-export-test", "2027-01-01 00:00:00.000Z")

    try:
        resp = await admin_client.get("/backoffice/ofertas/reporte-favoritos/exportar?tipo=paquete")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert resp.text.splitlines()[0] == "tipo,producto,veces_guardado"
        assert "paquete-export-test" in resp.text
    finally:
        await moc.eliminar("favoritos", fav["id"])
