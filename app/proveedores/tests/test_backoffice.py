"""WP-10 (auditoría de WorkPanels, 2026-07-31) — `proveedores_comerciales`,
antes solo un catálogo sembrado por script sin ningún panel de gestión."""

from app.proveedores.repositories.proveedores_repo import ProveedoresRepository


async def test_crear_y_listar_proveedor(pb, admin_client):
    resp = await admin_client.post(
        "/backoffice/proveedores",
        data={
            "nombre": "ProveedorWP10Test", "tipo_producto": "hotel",
            "comision_pactada_pct": 12.5, "contacto": "ventas@proveedor.test",
            "fecha_contrato": "2026-01-01",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "ProveedorWP10Test" in resp.text

    proveedor = await pb.get_first("proveedores_comerciales", 'nombre="ProveedorWP10Test"')
    assert proveedor is not None
    assert proveedor["activo"] is True
    await pb.delete_record("proveedores_comerciales", proveedor["id"])


async def test_editar_proveedor(pb, admin_client):
    proveedor = await pb.create_record(
        "proveedores_comerciales",
        {"nombre": "EditarWP10", "tipo_producto": "auto", "comision_pactada_pct": 5, "activo": True},
    )
    try:
        resp = await admin_client.post(
            f"/backoffice/proveedores/{proveedor['id']}",
            data={
                "nombre": "EditarWP10", "tipo_producto": "actividad",
                "comision_pactada_pct": 8, "contacto": "nuevo@contacto.test",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Proveedor actualizado" in resp.text

        actualizado = await pb.get_record("proveedores_comerciales", proveedor["id"])
        assert actualizado["tipo_producto"] == "actividad"
        assert actualizado["comision_pactada_pct"] == 8
    finally:
        await pb.delete_record("proveedores_comerciales", proveedor["id"])


async def test_desactivar_y_reactivar_proveedor(pb, admin_client):
    proveedor = await pb.create_record(
        "proveedores_comerciales",
        {"nombre": "AlternarWP10", "tipo_producto": "hotel", "activo": True},
    )
    try:
        resp = await admin_client.post(
            f"/backoffice/proveedores/{proveedor['id']}/alternar-activo", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "desactivado" in resp.text.lower()
        actualizado = await pb.get_record("proveedores_comerciales", proveedor["id"])
        assert actualizado["activo"] is False

        resp = await admin_client.post(
            f"/backoffice/proveedores/{proveedor['id']}/alternar-activo", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "reactivado" in resp.text.lower()
        actualizado = await pb.get_record("proveedores_comerciales", proveedor["id"])
        assert actualizado["activo"] is True
    finally:
        await pb.delete_record("proveedores_comerciales", proveedor["id"])


async def test_filtros_proveedores_backoffice(pb, admin_client):
    proveedor = await pb.create_record(
        "proveedores_comerciales",
        {"nombre": "FiltroUnicoWP10", "tipo_producto": "actividad", "activo": True},
    )
    try:
        resp = await admin_client.get(
            "/backoffice/proveedores", params={"nombre": "FiltroUnicoWP10"}
        )
        assert resp.status_code == 200
        assert "FiltroUnicoWP10" in resp.text

        resp = await admin_client.get(
            "/backoffice/proveedores", params={"tipo_producto": "hotel"}
        )
        assert resp.status_code == 200
        assert "FiltroUnicoWP10" not in resp.text  # es "actividad", no debe aparecer

        resp = await admin_client.get(
            "/backoffice/proveedores", params={"estado": "inactivo"}
        )
        assert resp.status_code == 200
        assert "FiltroUnicoWP10" not in resp.text  # está activo
    finally:
        await pb.delete_record("proveedores_comerciales", proveedor["id"])


async def test_agente_no_tiene_acceso_a_proveedores(agente_client):
    resp = await agente_client.get("/backoffice/proveedores")
    assert resp.status_code == 403
