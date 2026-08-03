"""RF-AYU-001,002,003 (CU-O97,O98,O99) — buscar/ver artículos, calificar."""

from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.shared import minio_operational_client as moc


async def _crear_articulo(pb, autor_id: str, **extra) -> dict:
    data = {
        "categoria": "Vuelos", "titulo": "Qué pasa si mi vuelo se retrasa",
        "contenido": "Te avisamos automáticamente y puedes elegir reembolso o cambio.",
        "autor_id": autor_id, "activo": True, "fecha_publicacion": "2027-01-01 00:00:00.000Z",
    }
    data.update(extra)
    return await pb.create_record("articulos_ayuda", data)


async def test_buscar_por_termino(client, pb, admin_client):
    articulo = await _crear_articulo(pb, admin_client.admin_usuario["id"], titulo="Retraso de vuelo real")

    resp = await client.get("/ayuda/buscar", params={"q": "retraso"})
    assert resp.status_code == 200
    assert "Retraso de vuelo real" in resp.text

    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_buscar_no_muestra_articulos_archivados(client, pb, admin_client):
    articulo = await _crear_articulo(
        pb, admin_client.admin_usuario["id"], titulo="Artículo archivado único", activo=False
    )

    resp = await client.get("/ayuda/buscar", params={"q": "archivado"})
    assert resp.status_code == 200
    assert "Artículo archivado único" not in resp.text

    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_ver_detalle_articulo(client, pb, admin_client):
    articulo = await _crear_articulo(pb, admin_client.admin_usuario["id"])

    resp = await client.get(f"/ayuda/{articulo['id']}")
    assert resp.status_code == 200
    assert "Qué pasa si mi vuelo se retrasa" in resp.text

    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_ver_detalle_articulo_inexistente_404(client):
    resp = await client.get("/ayuda/no-existe-este-id")
    assert resp.status_code == 404


async def test_ver_detalle_articulo_archivado_404(client, pb, admin_client):
    articulo = await _crear_articulo(pb, admin_client.admin_usuario["id"], activo=False)

    resp = await client.get(f"/ayuda/{articulo['id']}")
    assert resp.status_code == 404

    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_calificar_anonimo(client, pb, admin_client):
    articulo = await _crear_articulo(pb, admin_client.admin_usuario["id"])

    resp = await client.post(f"/ayuda/{articulo['id']}/calificar", data={"util": "arriba"}, follow_redirects=True)
    assert resp.status_code == 200

    calificaciones = await CentroAyudaRepository().calificaciones_de_articulo(articulo["id"])
    assert len(calificaciones) == 1
    assert calificaciones[0]["util"] == "arriba"
    assert not calificaciones[0].get("pasajero_id")

    for c in calificaciones:
        await moc.eliminar("articulo_calificaciones", c["id"])
    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_calificar_logueado_asocia_pasajero(client, pb, admin_client, pasajero_factory):
    articulo = await _crear_articulo(pb, admin_client.admin_usuario["id"])
    usuario, pasajero = await pasajero_factory()

    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303

    resp = await client.post(f"/ayuda/{articulo['id']}/calificar", data={"util": "abajo"}, follow_redirects=True)
    assert resp.status_code == 200

    calificaciones = await CentroAyudaRepository().calificaciones_de_articulo(articulo["id"])
    assert len(calificaciones) == 1
    assert calificaciones[0]["pasajero_id"] == pasajero["id"]

    for c in calificaciones:
        await moc.eliminar("articulo_calificaciones", c["id"])
    await pb.delete_record("articulos_ayuda", articulo["id"])


async def test_calificar_valor_invalido_no_crea_registro(client, pb, admin_client):
    articulo = await _crear_articulo(pb, admin_client.admin_usuario["id"])

    resp = await client.post(f"/ayuda/{articulo['id']}/calificar", data={"util": "regular"}, follow_redirects=True)
    assert resp.status_code == 200

    calificaciones = await CentroAyudaRepository().calificaciones_de_articulo(articulo["id"])
    assert calificaciones == []

    await pb.delete_record("articulos_ayuda", articulo["id"])
