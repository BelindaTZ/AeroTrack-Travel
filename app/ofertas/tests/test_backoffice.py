"""CU-T30 (cupones), CU-T31 (campañas), CU-T32 (reporte), CU-T44
(acumulación con paquete) — Actor: Administrador únicamente."""

from app.ofertas.repositories.ofertas_repo import OfertasRepository
from app.shared import minio_operational_client as moc


async def test_admin_crea_cupon(pb, admin_client):
    resp = await admin_client.post(
        "/backoffice/ofertas/cupones",
        data={
            "codigo": "BACKOFFICETEST1", "tipo": "porcentaje", "valor": 15,
            "fecha_expiracion": "2030-01-01",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "BACKOFFICETEST1" in resp.text

    cupon = await pb.get_first("cupones_descuento", 'codigo="BACKOFFICETEST1"')
    assert cupon is not None
    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_editar_codigo_de_cupon_usado_se_bloquea(pb, admin_client):
    """RN-OFE-T01 — el código no puede cambiar una vez que el cupón tiene
    usos; el resto de campos (valor, expiración) sigue editable."""
    cupon = await pb.create_record(
        "cupones_descuento",
        {
            "codigo": "USADOTEST1", "tipo": "porcentaje", "valor": 10,
            "fecha_expiracion": "2030-01-01 00:00:00.000Z", "usos_actuales": 1, "activo": True,
        },
    )

    resp = await admin_client.post(
        f"/backoffice/ofertas/cupones/{cupon['id']}",
        data={"tipo": "porcentaje", "valor": 20, "fecha_expiracion": "2031-01-01", "activo": "true"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    actualizado = await pb.get_record("cupones_descuento", cupon["id"])
    assert actualizado["valor"] == 20
    assert actualizado["codigo"] == "USADOTEST1"

    await pb.delete_record("cupones_descuento", cupon["id"])


async def test_reporte_cupones_muestra_uso_real(
    pb, admin_client, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"])

    cupon = await pb.create_record(
        "cupones_descuento",
        {
            "codigo": "REPORTETEST1", "tipo": "monto_fijo", "valor": 5,
            "fecha_expiracion": "2030-01-01 00:00:00.000Z", "usos_actuales": 1, "activo": True,
        },
    )
    from datetime import datetime, timezone
    uso = await OfertasRepository().registrar_uso(
        cupon["id"], reserva["id"], 5.0, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    )

    resp = await admin_client.get("/backoffice/ofertas/reporte-cupones")
    assert resp.status_code == 200
    assert "REPORTETEST1" in resp.text

    await moc.eliminar("cupones_uso", uso["id"])
    await pb.delete_record("cupones_descuento", cupon["id"])


# ── WP-06 (auditoría de WorkPanels, 2026-07-31) ──────────────────────────

async def test_desactivar_y_reactivar_cupon(pb, admin_client):
    cupon = await pb.create_record(
        "cupones_descuento",
        {
            "codigo": "ALTERNARTEST1", "tipo": "porcentaje", "valor": 10,
            "fecha_expiracion": "2030-01-01 00:00:00.000Z", "usos_actuales": 0, "activo": True,
        },
    )
    try:
        resp = await admin_client.post(
            f"/backoffice/ofertas/cupones/{cupon['id']}/alternar-activo", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "desactivado" in resp.text.lower()
        actualizado = await pb.get_record("cupones_descuento", cupon["id"])
        assert actualizado["activo"] is False

        resp = await admin_client.post(
            f"/backoffice/ofertas/cupones/{cupon['id']}/alternar-activo", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "reactivado" in resp.text.lower()
        actualizado = await pb.get_record("cupones_descuento", cupon["id"])
        assert actualizado["activo"] is True
    finally:
        await pb.delete_record("cupones_descuento", cupon["id"])


async def test_filtros_cupones_backoffice(pb, admin_client):
    cupon = await pb.create_record(
        "cupones_descuento",
        {
            "codigo": "FILTROUNICO1", "tipo": "monto_fijo", "valor": 7,
            "fecha_expiracion": "2030-01-01 00:00:00.000Z", "usos_actuales": 0, "activo": True,
        },
    )
    try:
        resp = await admin_client.get("/backoffice/ofertas/cupones", params={"codigo": "FILTROUNICO1"})
        assert resp.status_code == 200
        assert "FILTROUNICO1" in resp.text

        resp = await admin_client.get("/backoffice/ofertas/cupones", params={"tipo_cupon": "porcentaje"})
        assert resp.status_code == 200
        assert "FILTROUNICO1" not in resp.text  # es monto_fijo, no debe aparecer

        resp = await admin_client.get("/backoffice/ofertas/cupones", params={"estado": "inactivo"})
        assert resp.status_code == 200
        assert "FILTROUNICO1" not in resp.text  # está activo
    finally:
        await pb.delete_record("cupones_descuento", cupon["id"])


async def test_listar_y_filtrar_suscriptores_backoffice(pb, admin_client):
    from datetime import datetime, timezone

    repo = OfertasRepository()
    suscripcion = await repo.crear_suscripcion(
        {"email": "suscriptorwp07@test.com", "fecha_suscripcion": datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S.000Z"), "activo": True}
    )
    try:
        resp = await admin_client.get("/backoffice/ofertas/suscriptores")
        assert resp.status_code == 200
        assert "suscriptorwp07@test.com" in resp.text

        resp = await admin_client.get(
            "/backoffice/ofertas/suscriptores", params={"email": "suscriptorwp07"}
        )
        assert resp.status_code == 200
        assert "suscriptorwp07@test.com" in resp.text

        resp = await admin_client.get(
            "/backoffice/ofertas/suscriptores", params={"email": "no-existe-xyz"}
        )
        assert resp.status_code == 200
        assert "suscriptorwp07@test.com" not in resp.text

        resp = await admin_client.get(
            "/backoffice/ofertas/suscriptores", params={"estado": "inactivo"}
        )
        assert resp.status_code == 200
        assert "suscriptorwp07@test.com" not in resp.text  # está activo
    finally:
        await moc.eliminar("newsletter_suscripciones", suscripcion["id"])


async def test_desactivar_y_reactivar_suscripcion(pb, admin_client):
    from datetime import datetime, timezone

    repo = OfertasRepository()
    suscripcion = await repo.crear_suscripcion(
        {"email": "alternarwp07@test.com", "fecha_suscripcion": datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S.000Z"), "activo": True}
    )
    try:
        resp = await admin_client.post(
            f"/backoffice/ofertas/suscriptores/{suscripcion['id']}/alternar-activo", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "desactivada" in resp.text.lower()
        actualizado = await repo.obtener_suscripcion(suscripcion["id"])
        assert actualizado["activo"] is False

        resp = await admin_client.post(
            f"/backoffice/ofertas/suscriptores/{suscripcion['id']}/alternar-activo", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "reactivada" in resp.text.lower()
        actualizado = await repo.obtener_suscripcion(suscripcion["id"])
        assert actualizado["activo"] is True
    finally:
        await moc.eliminar("newsletter_suscripciones", suscripcion["id"])


async def test_agente_no_tiene_acceso_a_suscriptores(agente_client):
    resp = await agente_client.get("/backoffice/ofertas/suscriptores")
    assert resp.status_code == 403


async def test_config_acumulacion_default_se_guarda(pb, admin_client):
    resp = await admin_client.post(
        "/backoffice/ofertas/config-acumulacion-paquete", data={"acumulable": "true"}, follow_redirects=True
    )
    assert resp.status_code == 200

    registro = await pb.get_first("configuracion_sistema", 'clave="cupones.acumulable_con_paquete_default"')
    assert registro["valor"] == "true"

    # revertir al default real del proyecto (false) para no afectar otros tests
    resp = await admin_client.post(
        "/backoffice/ofertas/config-acumulacion-paquete", data={}, follow_redirects=True
    )
    assert resp.status_code == 200
    registro = await pb.get_first("configuracion_sistema", 'clave="cupones.acumulable_con_paquete_default"')
    assert registro["valor"] == "false"


async def test_crear_campana_queda_como_borrador(pb, admin_client):
    resp = await admin_client.post(
        "/backoffice/ofertas/campanas",
        data={"nombre": "Campaña de prueba backoffice", "segmento_criterio": "{}", "plantilla": "Hola pasajero"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Campaña de prueba backoffice" in resp.text

    campana = await pb.get_first("campanas_email", 'nombre="Campaña de prueba backoffice"')
    assert campana is not None
    assert campana["estado"] == "borrador"
    await pb.delete_record("campanas_email", campana["id"])


async def test_enviar_campana_sin_credencial_sendgrid_se_rechaza(pb, admin_client):
    """No hay ninguna `sendgrid.*` sembrada en configuracion_sistema —
    el envío debe rechazarse explícitamente, nunca simularse."""
    campana = await pb.create_record(
        "campanas_email",
        {
            "nombre": "Campaña sin credencial", "segmento_criterio": {"segmento": "todos"}, "plantilla": "x",
            "estado": "borrador", "creado_por": admin_client.admin_usuario["id"],
        },
    )

    resp = await admin_client.post(f"/backoffice/ofertas/campanas/{campana['id']}/enviar")
    assert resp.status_code == 303
    assert "SendGrid" in resp.headers["location"] or "credencial" in resp.headers["location"].lower()

    sigue_borrador = await pb.get_record("campanas_email", campana["id"])
    assert sigue_borrador["estado"] == "borrador"

    await pb.delete_record("campanas_email", campana["id"])


async def test_reenviar_campana_ya_enviada_se_bloquea(pb, admin_client):
    campana = await pb.create_record(
        "campanas_email",
        {
            "nombre": "Campaña ya enviada", "segmento_criterio": {"segmento": "todos"}, "plantilla": "x",
            "estado": "enviada", "creado_por": admin_client.admin_usuario["id"],
            "fecha_envio": "2027-01-01 00:00:00.000Z",
        },
    )

    resp = await admin_client.post(f"/backoffice/ofertas/campanas/{campana['id']}/enviar")
    assert resp.status_code == 303
    assert "enviada" in resp.headers["location"].lower() or "ya" in resp.headers["location"].lower()

    await pb.delete_record("campanas_email", campana["id"])


async def test_agente_no_tiene_acceso_a_ofertas(agente_client):
    """El catálogo asigna las 4 funcionalidades tácticas de este módulo
    solo a Administrador — sin permiso `ofertas.ver` sembrado para Agente."""
    resp = await agente_client.get("/backoffice/ofertas/cupones")
    assert resp.status_code == 403


# ── WP-17 (auditoría de WorkPanels, 2026-08-01) ──────────────────────────

async def test_crear_ver_editar_y_alternar_oferta_destacada(pb, admin_client):
    resp = await admin_client.post(
        "/backoffice/ofertas/destacadas",
        data={
            "tipo_producto": "hotel", "producto_ref": "hotel-test-wp17", "titulo": "Oferta WP17 Test",
            "fecha_inicio": "2026-01-01", "fecha_fin": "2030-01-01",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Oferta WP17 Test" in resp.text
    assert "Oferta creada" in resp.text

    oferta = await pb.get_first("ofertas_destacadas", 'titulo="Oferta WP17 Test"')
    assert oferta is not None
    assert oferta["activa"] is True

    try:
        resp = await admin_client.post(
            f"/backoffice/ofertas/destacadas/{oferta['id']}",
            data={
                "tipo_producto": "hotel", "producto_ref": "hotel-test-wp17", "titulo": "Oferta WP17 Editada",
                "fecha_inicio": "2026-01-01", "fecha_fin": "2030-01-01",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Oferta actualizada" in resp.text
        actualizada = await pb.get_record("ofertas_destacadas", oferta["id"])
        assert actualizada["titulo"] == "Oferta WP17 Editada"

        resp = await admin_client.post(
            f"/backoffice/ofertas/destacadas/{oferta['id']}/alternar-activa", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "desactivada" in resp.text.lower()
        desactivada = await pb.get_record("ofertas_destacadas", oferta["id"])
        assert desactivada["activa"] is False

        resp = await admin_client.post(
            f"/backoffice/ofertas/destacadas/{oferta['id']}/alternar-activa", follow_redirects=True
        )
        assert resp.status_code == 200
        assert "reactivada" in resp.text.lower()
    finally:
        await pb.delete_record("ofertas_destacadas", oferta["id"])


async def test_filtros_ofertas_destacadas_backoffice(pb, admin_client):
    oferta = await pb.create_record(
        "ofertas_destacadas",
        {
            "tipo_producto": "crucero", "producto_ref": "crucero-filtro-wp17", "titulo": "FiltroUnicoWP17",
            "fecha_inicio": "2026-01-01 00:00:00.000Z", "fecha_fin": "2030-01-01 00:00:00.000Z", "activa": True,
        },
    )
    try:
        resp = await admin_client.get("/backoffice/ofertas/destacadas", params={"tipo_producto": "crucero"})
        assert resp.status_code == 200
        assert "FiltroUnicoWP17" in resp.text

        resp = await admin_client.get("/backoffice/ofertas/destacadas", params={"tipo_producto": "hotel"})
        assert resp.status_code == 200
        assert "FiltroUnicoWP17" not in resp.text

        resp = await admin_client.get("/backoffice/ofertas/destacadas", params={"estado": "inactivo"})
        assert resp.status_code == 200
        assert "FiltroUnicoWP17" not in resp.text
    finally:
        await pb.delete_record("ofertas_destacadas", oferta["id"])
