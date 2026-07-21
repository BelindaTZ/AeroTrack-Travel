"""RF-OFE-001,002,004,005 (CU-O101,O102,O104,O105) — ofertas destacadas,
destinos populares, newsletter, términos."""

import datetime
import uuid


async def _crear_oferta(pb, **extra) -> dict:
    hoy = datetime.date.today()
    data = {
        "tipo_producto": "vuelo", "producto_ref": "no-existe", "titulo": "Oferta de prueba",
        "descripcion": "Descripción real de prueba",
        "fecha_inicio": (hoy - datetime.timedelta(days=1)).isoformat(),
        "fecha_fin": (hoy + datetime.timedelta(days=30)).isoformat(),
        "activa": True,
    }
    data.update(extra)
    return await pb.create_record("ofertas_destacadas", data)


async def test_listar_ofertas_vigentes(client, pb):
    oferta = await _crear_oferta(pb, titulo="Oferta vigente única")
    resp = await client.get("/ofertas")
    assert resp.status_code == 200
    assert "Oferta vigente única" in resp.text
    await pb.delete_record("ofertas_destacadas", oferta["id"])


async def test_oferta_expirada_no_aparece(client, pb):
    hoy = datetime.date.today()
    oferta = await _crear_oferta(
        pb, titulo="Oferta ya vencida única",
        fecha_inicio=(hoy - datetime.timedelta(days=60)).isoformat(),
        fecha_fin=(hoy - datetime.timedelta(days=1)).isoformat(),
    )
    resp = await client.get("/ofertas")
    assert resp.status_code == 200
    assert "Oferta ya vencida única" not in resp.text
    await pb.delete_record("ofertas_destacadas", oferta["id"])


async def test_filtrar_ofertas_por_tipo_producto(client, pb):
    oferta_vuelo = await _crear_oferta(pb, tipo_producto="vuelo", titulo="Oferta de vuelo filtrable")
    oferta_hotel = await _crear_oferta(pb, tipo_producto="hotel", titulo="Oferta de hotel filtrable")

    resp = await client.get("/ofertas", params={"tipo_producto": "hotel"})
    assert resp.status_code == 200
    assert "Oferta de hotel filtrable" in resp.text
    assert "Oferta de vuelo filtrable" not in resp.text

    await pb.delete_record("ofertas_destacadas", oferta_vuelo["id"])
    await pb.delete_record("ofertas_destacadas", oferta_hotel["id"])


async def test_ver_terminos_de_oferta(client, pb):
    oferta = await _crear_oferta(pb, descripcion="Términos completos y reales de la oferta")
    resp = await client.get(f"/ofertas/{oferta['id']}/terminos")
    assert resp.status_code == 200
    assert "Términos completos y reales de la oferta" in resp.text
    await pb.delete_record("ofertas_destacadas", oferta["id"])


async def test_terminos_oferta_inexistente_404(client):
    resp = await client.get("/ofertas/no-existe-este-id/terminos")
    assert resp.status_code == 404


async def test_suscribirse_newsletter_sin_cuenta(client, pb):
    email = f"suscriptor.{uuid.uuid4().hex[:8]}@aerotrack.test"
    resp = await client.post("/newsletter/suscribirse", data={"email": email}, follow_redirects=True)
    assert resp.status_code == 200

    suscripcion = await pb.get_first("newsletter_suscripciones", f'email="{email}"')
    assert suscripcion is not None
    assert suscripcion["pasajero_id"] == ""
    await pb.delete_record("newsletter_suscripciones", suscripcion["id"])


async def test_suscribirse_newsletter_logueado_asocia_pasajero(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303

    resp = await client.post(
        "/newsletter/suscribirse", data={"email": usuario["email"]}, follow_redirects=True
    )
    assert resp.status_code == 200

    suscripcion = await pb.get_first("newsletter_suscripciones", f'email="{usuario["email"]}"')
    assert suscripcion is not None
    assert suscripcion["pasajero_id"] == pasajero["id"]
    await pb.delete_record("newsletter_suscripciones", suscripcion["id"])


async def test_destinos_populares_sin_origen_muestra_formulario(client):
    resp = await client.get("/destinos-populares")
    assert resp.status_code == 200
    assert "Destinos populares" in resp.text


async def test_destinos_populares_con_origen_agrega_busquedas_reales(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    busqueda = await pb.create_record(
        "busquedas_recientes",
        {
            "pasajero_id": pasajero["id"], "tipo_producto": "vuelo",
            "criterios": {"origen": "ZZZ", "destino": "YYY", "fecha": "2027-01-01"},
            "fecha": "2027-01-01 00:00:00.000Z",
        },
    )

    resp = await client.get("/destinos-populares", params={"origen": "ZZZ"})
    assert resp.status_code == 200
    assert "YYY" in resp.text

    await pb.delete_record("busquedas_recientes", busqueda["id"])


async def test_destinos_populares_infiere_origen_del_historial_del_pasajero(client, pb, pasajero_factory):
    """Regresión: el origen INFERIDO (sin `?origen=` en la URL) debía
    mostrarse en pantalla igual que el declarado explícitamente — un bug
    real pasaba el query param crudo (vacío) a la plantilla en vez del
    origen que el servicio realmente usó, dejando la sección de
    resultados sin renderizar aunque el cálculo interno fuera correcto."""
    usuario, pasajero = await pasajero_factory()
    busqueda = await pb.create_record(
        "busquedas_recientes",
        {
            "pasajero_id": pasajero["id"], "tipo_producto": "vuelo",
            "criterios": {"origen": "QQQ", "destino": "WWW", "fecha": "2027-01-01"},
            "fecha": "2027-01-01 00:00:00.000Z",
        },
    )

    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303

    resp = await client.get("/destinos-populares")
    assert resp.status_code == 200
    assert "QQQ" in resp.text
    assert "WWW" in resp.text

    await pb.delete_record("busquedas_recientes", busqueda["id"])
