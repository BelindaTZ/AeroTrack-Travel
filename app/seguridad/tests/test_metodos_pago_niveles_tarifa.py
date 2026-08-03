"""WP-18 (auditoría de WorkPanels, 2026-08-01) — métodos de pago y
niveles de tarifa, antes solo gestionables editando la base o
re-corriendo un script de seed."""


async def test_crear_editar_y_alternar_metodo_pago(pb, admin_client):
    resp = await admin_client.post(
        "/admin/configuracion/metodos-pago",
        data={"nombre": "MetodoWP18Test", "tipo": "tarjeta_credito", "procesador": "stripe"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "MetodoWP18Test" in resp.text
    assert "Método de pago creado" in resp.text

    metodo = await pb.get_first("metodos_pago", 'nombre="MetodoWP18Test"')
    assert metodo is not None
    assert metodo["activo"] is True

    try:
        resp = await admin_client.post(
            f"/admin/configuracion/metodos-pago/{metodo['id']}",
            data={"nombre": "MetodoWP18Test", "tipo": "tarjeta_debito", "procesador": "stripe"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Método de pago actualizado" in resp.text
        actualizado = await pb.get_record("metodos_pago", metodo["id"])
        assert actualizado["tipo"] == "tarjeta_debito"

        resp = await admin_client.post(
            f"/admin/configuracion/metodos-pago/{metodo['id']}/alternar-activo", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "desactivado" in resp.text.lower()
        desactivado = await pb.get_record("metodos_pago", metodo["id"])
        assert desactivado["activo"] is False

        resp = await admin_client.post(
            f"/admin/configuracion/metodos-pago/{metodo['id']}/alternar-activo", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "reactivado" in resp.text.lower()
    finally:
        await pb.delete_record("metodos_pago", metodo["id"])


async def test_no_se_puede_desactivar_el_unico_metodo_activo(pb, admin_client):
    activos_existentes = await pb.list_records("metodos_pago", {"filter": "activo=true", "perPage": 200})
    # desactivamos todos los demás temporalmente para dejar solo el nuestro
    otros_reactivar = []
    for m in activos_existentes["items"]:
        await pb.update_record("metodos_pago", m["id"], {"activo": False})
        otros_reactivar.append(m["id"])

    metodo = await pb.create_record(
        "metodos_pago", {"nombre": "UnicoActivoWP18", "tipo": "tarjeta_credito", "procesador": "stripe", "activo": True}
    )
    try:
        resp = await admin_client.post(
            f"/admin/configuracion/metodos-pago/{metodo['id']}/alternar-activo", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "único método de pago activo" in resp.text.lower() or "unico" in resp.text.lower()
        sin_cambios = await pb.get_record("metodos_pago", metodo["id"])
        assert sin_cambios["activo"] is True
    finally:
        await pb.delete_record("metodos_pago", metodo["id"])
        for mid in otros_reactivar:
            await pb.update_record("metodos_pago", mid, {"activo": True})


async def test_crear_y_editar_nivel_tarifa(pb, admin_client):
    politica = await pb.get_first("politicas_reembolso", "")
    assert politica is not None, "seed_seguridad.py debe haber sembrado al menos una política de reembolso"

    resp = await admin_client.post(
        "/admin/configuracion/niveles-tarifa",
        data={
            "nombre": "NivelWP18Test", "descripcion": "nivel de prueba",
            "politica_reembolso_id": politica["id"], "equipaje_incluido": "true",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "NivelWP18Test" in resp.text
    assert "Nivel de tarifa creado" in resp.text

    nivel = await pb.get_first("niveles_tarifa", 'nombre="NivelWP18Test"')
    assert nivel is not None
    assert nivel["equipaje_incluido"] is True

    try:
        resp = await admin_client.post(
            f"/admin/configuracion/niveles-tarifa/{nivel['id']}",
            data={
                "nombre": "NivelWP18Editado", "descripcion": "editado",
                "politica_reembolso_id": politica["id"], "cambios_permitidos": "true",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Nivel de tarifa actualizado" in resp.text
        actualizado = await pb.get_record("niveles_tarifa", nivel["id"])
        assert actualizado["nombre"] == "NivelWP18Editado"
        assert actualizado["cambios_permitidos"] is True
        assert actualizado["equipaje_incluido"] is False  # no se mandó en el segundo submit
    finally:
        await pb.delete_record("niveles_tarifa", nivel["id"])


async def test_agente_no_tiene_acceso_a_metodos_pago_ni_niveles_tarifa(agente_client):
    resp = await agente_client.get("/admin/configuracion/metodos-pago")
    assert resp.status_code == 403
    resp = await agente_client.get("/admin/configuracion/niveles-tarifa")
    assert resp.status_code == 403
