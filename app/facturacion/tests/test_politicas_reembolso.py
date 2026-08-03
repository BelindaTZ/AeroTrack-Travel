"""CU-T18 — políticas de reembolso (WP-09, auditoría de WorkPanels
2026-07-31): filtros + paginación agregados sobre el panel existente."""

from app.facturacion.repositories.facturacion_repo import FacturacionRepository


async def test_crear_y_listar_politica_reembolso(pb, admin_client):
    resp = await admin_client.post(
        "/backoffice/politicas-reembolso",
        data={
            "nombre": "PoliticaWP09Test", "condiciones": "Cancelación con 48h de anticipación",
            "porcentaje_reembolso": 80, "ventana_horas": 48,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "PoliticaWP09Test" in resp.text

    politica = await pb.get_first("politicas_reembolso", 'nombre="PoliticaWP09Test"')
    assert politica is not None
    await pb.delete_record("politicas_reembolso", politica["id"])


async def test_editar_politica_reembolso(pb, admin_client):
    politica = await pb.create_record(
        "politicas_reembolso",
        {"nombre": "EditarWP09", "condiciones": "Original", "porcentaje_reembolso": 50, "ventana_horas": 24},
    )
    try:
        resp = await admin_client.post(
            f"/backoffice/politicas-reembolso/{politica['id']}",
            data={
                "nombre": "EditarWP09", "condiciones": "Modificada",
                "porcentaje_reembolso": 70, "ventana_horas": 12,
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Política actualizada" in resp.text

        actualizada = await pb.get_record("politicas_reembolso", politica["id"])
        assert actualizada["condiciones"] == "Modificada"
        assert actualizada["porcentaje_reembolso"] == 70
    finally:
        await pb.delete_record("politicas_reembolso", politica["id"])


async def test_filtro_nombre_politicas_reembolso(pb, admin_client):
    politica = await pb.create_record(
        "politicas_reembolso",
        {"nombre": "FiltroUnicoWP09", "condiciones": "x", "porcentaje_reembolso": 10, "ventana_horas": 1},
    )
    try:
        resp = await admin_client.get(
            "/backoffice/politicas-reembolso", params={"nombre": "FiltroUnicoWP09"}
        )
        assert resp.status_code == 200
        assert "FiltroUnicoWP09" in resp.text

        resp = await admin_client.get(
            "/backoffice/politicas-reembolso", params={"nombre": "no-existe-xyz"}
        )
        assert resp.status_code == 200
        assert "FiltroUnicoWP09" not in resp.text
    finally:
        await pb.delete_record("politicas_reembolso", politica["id"])

