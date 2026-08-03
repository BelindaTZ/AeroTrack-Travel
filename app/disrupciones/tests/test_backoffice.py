"""WP-12 (auditoría de WorkPanels, 2026-07-31) — antes solo existía la
configuración del umbral de riesgo global; no había forma de listar o
corregir manualmente una disrupción individual desde el backoffice."""

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.shared import minio_operational_client as moc


async def test_listar_y_filtrar_disrupciones(admin_client, vuelo_factory):
    vuelo = await vuelo_factory()
    repo = DisrupcionesRepository()
    disrupcion = await repo.crear_disrupcion(
        {
            "vuelo_id": vuelo["id"], "fuente_deteccion": "api_real", "tipo_cambio": "retraso",
            "estado": "activa", "detalle": "Retraso de 45 minutos WP12", "fecha_deteccion": "2027-01-01 00:00:00.000Z",
        }
    )
    try:
        resp = await admin_client.get("/backoffice/disrupciones")
        assert resp.status_code == 200
        assert vuelo["numero_vuelo"] in resp.text

        resp = await admin_client.get("/backoffice/disrupciones", params={"estado": "resuelta"})
        assert resp.status_code == 200
        assert vuelo["numero_vuelo"] not in resp.text

        resp = await admin_client.get("/backoffice/disrupciones", params={"tipo_cambio": "cancelacion"})
        assert resp.status_code == 200
        assert vuelo["numero_vuelo"] not in resp.text
    finally:
        await moc.eliminar("disrupciones", disrupcion["id"])


async def test_resolver_disrupcion_manual(admin_client, vuelo_factory):
    vuelo = await vuelo_factory()
    repo = DisrupcionesRepository()
    disrupcion = await repo.crear_disrupcion(
        {
            "vuelo_id": vuelo["id"], "fuente_deteccion": "monitor_correo", "tipo_cambio": "cancelacion",
            "estado": "activa", "detalle": "x", "fecha_deteccion": "2027-01-01 00:00:00.000Z",
        }
    )
    try:
        resp = await admin_client.post(f"/backoffice/disrupciones/{disrupcion['id']}/resolver", follow_redirects=True)
        assert resp.status_code == 200
        assert "Disrupción marcada como resuelta" in resp.text

        actualizada = await repo.obtener_disrupcion(disrupcion["id"])
        assert actualizada["estado"] == "resuelta"

        # ya resuelta — segunda llamada debe rechazarse, no reprocesar
        resp = await admin_client.post(f"/backoffice/disrupciones/{disrupcion['id']}/resolver", follow_redirects=True)
        assert resp.status_code == 200
        assert "ya estaba resuelta" in resp.text
    finally:
        await moc.eliminar("disrupciones", disrupcion["id"])


async def test_agente_puede_ver_pero_no_resolver_disrupciones(agente_client, vuelo_factory):
    # Agente tiene "ver" en disrupciones (seed_seguridad.py) pero no
    # "editar" — solo admin_operaciones puede marcar una como resuelta.
    resp = await agente_client.get("/backoffice/disrupciones")
    assert resp.status_code == 200

    vuelo = await vuelo_factory()
    repo = DisrupcionesRepository()
    disrupcion = await repo.crear_disrupcion(
        {
            "vuelo_id": vuelo["id"], "fuente_deteccion": "api_real", "tipo_cambio": "retraso",
            "estado": "activa", "detalle": "x", "fecha_deteccion": "2027-01-01 00:00:00.000Z",
        }
    )
    try:
        resp = await agente_client.post(f"/backoffice/disrupciones/{disrupcion['id']}/resolver")
        assert resp.status_code == 403
    finally:
        await moc.eliminar("disrupciones", disrupcion["id"])
