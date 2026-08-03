"""RF-CTA-006/RN-CTA-002 — saldo vigente del programa de beneficios,
excluyendo puntos vencidos según el nivel."""

import datetime

from app.cuenta.services.cuenta_service import resumen_puntos
from app.shared import minio_operational_client as moc


async def _login(client, usuario):
    resp = await client.post("/login", data={"email": usuario["email"], "password": usuario["_password"]})
    assert resp.status_code == 303


async def _crear_movimiento(pasajero_id: str, tipo: str, puntos: int, fecha: str) -> dict:
    id_ = moc.generar_id()
    return await moc.crear(
        "programa_beneficios_movimientos",
        id_,
        {"id": id_, "pasajero_id": pasajero_id, "tipo": tipo, "puntos": puntos, "fecha": fecha},
    )


async def test_sin_movimientos_saldo_cero_y_sin_nivel(pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    resumen = await resumen_puntos(pasajero["id"])
    assert resumen.saldo_vigente == 0
    assert resumen.nivel_actual is None
    assert resumen.movimientos == []


async def test_saldo_suma_acumulacion_y_resta_redencion(pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    hoy = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    m1 = await _crear_movimiento(pasajero["id"], "acumulacion", 100, hoy)
    m2 = await _crear_movimiento(pasajero["id"], "redencion", 30, hoy)

    resumen = await resumen_puntos(pasajero["id"])
    assert resumen.saldo_vigente == 70

    await moc.eliminar("programa_beneficios_movimientos", m1["id"])
    await moc.eliminar("programa_beneficios_movimientos", m2["id"])


async def test_puntos_vencidos_no_cuentan_en_saldo_vigente(pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    # `puntos_minimos=70` (no 0) a propósito: igual al saldo bruto que este
    # test genera (50+20) — así el nivel de prueba sigue ganando sin
    # importar qué otros niveles reales (Bronce/Plata/Oro/...) existan ya
    # en la colección compartida (`resumen_puntos` toma el de mayor umbral
    # satisfecho, ver cuenta_service.py).
    nivel = await pb.create_record(
        "programa_beneficios_niveles",
        {"nombre_nivel": "NivelTestVencimiento", "puntos_minimos": 70, "vencimiento_meses": 6},
    )
    hace_un_anio = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=400)).strftime(
        "%Y-%m-%d %H:%M:%S.000Z"
    )
    hoy = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    viejo = await _crear_movimiento(pasajero["id"], "acumulacion", 50, hace_un_anio)
    nuevo = await _crear_movimiento(pasajero["id"], "acumulacion", 20, hoy)

    resumen = await resumen_puntos(pasajero["id"])
    assert resumen.saldo_vigente == 20
    assert resumen.nivel_actual == "NivelTestVencimiento"
    vigentes = {m.puntos: m.vigente for m in resumen.movimientos}
    assert vigentes[50] is False
    assert vigentes[20] is True

    await moc.eliminar("programa_beneficios_movimientos", viejo["id"])
    await moc.eliminar("programa_beneficios_movimientos", nuevo["id"])
    await pb.delete_record("programa_beneficios_niveles", nivel["id"])


async def test_endpoint_puntos_requiere_sesion(client):
    resp = await client.get("/mi-cuenta/puntos")
    assert resp.status_code in (303, 307)


async def test_endpoint_puntos_muestra_saldo(client, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    hoy = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    mov = await _crear_movimiento(pasajero["id"], "acumulacion", 15, hoy)

    await _login(client, usuario)
    resp = await client.get("/mi-cuenta/puntos")
    assert resp.status_code == 200
    assert "15" in resp.text

    await moc.eliminar("programa_beneficios_movimientos", mov["id"])
