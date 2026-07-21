"""RF-CTA-006/RN-CTA-002 — saldo vigente del programa de beneficios,
excluyendo puntos vencidos según el nivel."""

import datetime

from app.cuenta.services.cuenta_service import resumen_puntos


async def _login(client, usuario):
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303


async def test_sin_movimientos_saldo_cero_y_sin_nivel(pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    resumen = await resumen_puntos(pasajero["id"])
    assert resumen.saldo_vigente == 0
    assert resumen.nivel_actual is None
    assert resumen.movimientos == []


async def test_saldo_suma_acumulacion_y_resta_redencion(pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    hoy = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    m1 = await pb.create_record(
        "programa_beneficios_movimientos",
        {"pasajero_id": pasajero["id"], "tipo": "acumulacion", "puntos": 100, "fecha": hoy},
    )
    m2 = await pb.create_record(
        "programa_beneficios_movimientos",
        {"pasajero_id": pasajero["id"], "tipo": "redencion", "puntos": 30, "fecha": hoy},
    )

    resumen = await resumen_puntos(pasajero["id"])
    assert resumen.saldo_vigente == 70

    await pb.delete_record("programa_beneficios_movimientos", m1["id"])
    await pb.delete_record("programa_beneficios_movimientos", m2["id"])


async def test_puntos_vencidos_no_cuentan_en_saldo_vigente(pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    nivel = await pb.create_record(
        "programa_beneficios_niveles",
        {"nombre_nivel": "NivelTestVencimiento", "puntos_minimos": 0, "vencimiento_meses": 6},
    )
    hace_un_anio = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=400)).strftime(
        "%Y-%m-%d %H:%M:%S.000Z"
    )
    hoy = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    viejo = await pb.create_record(
        "programa_beneficios_movimientos",
        {"pasajero_id": pasajero["id"], "tipo": "acumulacion", "puntos": 50, "fecha": hace_un_anio},
    )
    nuevo = await pb.create_record(
        "programa_beneficios_movimientos",
        {"pasajero_id": pasajero["id"], "tipo": "acumulacion", "puntos": 20, "fecha": hoy},
    )

    resumen = await resumen_puntos(pasajero["id"])
    assert resumen.saldo_vigente == 20
    assert resumen.nivel_actual == "NivelTestVencimiento"
    vigentes = {m.puntos: m.vigente for m in resumen.movimientos}
    assert vigentes[50] is False
    assert vigentes[20] is True

    await pb.delete_record("programa_beneficios_movimientos", viejo["id"])
    await pb.delete_record("programa_beneficios_movimientos", nuevo["id"])
    await pb.delete_record("programa_beneficios_niveles", nivel["id"])


async def test_endpoint_puntos_requiere_sesion(client):
    resp = await client.get("/mi-cuenta/puntos")
    assert resp.status_code in (303, 307)


async def test_endpoint_puntos_muestra_saldo(client, pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    hoy = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    mov = await pb.create_record(
        "programa_beneficios_movimientos",
        {"pasajero_id": pasajero["id"], "tipo": "acumulacion", "puntos": 15, "fecha": hoy},
    )

    await _login(client, usuario)
    resp = await client.get("/mi-cuenta/puntos")
    assert resp.status_code == 200
    assert "15" in resp.text

    await pb.delete_record("programa_beneficios_movimientos", mov["id"])
