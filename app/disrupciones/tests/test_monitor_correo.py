import uuid

import pytest

from app.disrupciones.services.deteccion_service import parsear_correo_a_disrupcion
from app.disrupciones.services.monitor_correo_service import monitorear_correo


def _correo(asunto: str, cuerpo: str = "") -> dict:
    return {
        "asunto": asunto,
        "remitente": "notificaciones@aerolinea.com",
        "cuerpo_texto": cuerpo,
        "fecha": "2026-07-10T12:00:00+00:00",
    }


def _numero_vuelo_realista() -> str:
    # El default de `vuelo_factory` ("TST" + hex) no tiene forma de código
    # IATA real (2 letras + 2-4 dígitos) — el parseo de correos sí la
    # exige, como cualquier aviso real de aerolínea.
    return f"DL{uuid.uuid4().int % 9000 + 1000}"


# ── CHK002, CHK018 ──────────────────────────────────────────────────────

async def test_correo_con_cambio_valido_genera_disrupcion(
    pb, vuelo_factory, gmail_client_falso, notification_sender_falso
):
    vuelo = await vuelo_factory(estado="programado", numero_vuelo=_numero_vuelo_realista())
    correo = _correo(f"Flight {vuelo['numero_vuelo']} Cancelled", "Your flight has been cancelled.")
    cliente = gmail_client_falso([correo])

    resumen = await monitorear_correo(cliente, notification_sender_falso)
    assert resumen["disrupciones_creadas"] == 1
    assert resumen["descartados"] == 0

    disrupcion = await pb.get_first(
        "disrupciones", f'vuelo_id="{vuelo["id"]}" && fuente_deteccion="monitor_correo"'
    )
    assert disrupcion is not None
    assert disrupcion["tipo_cambio"] == "cancelacion"

    vuelo_actualizado = await pb.get_record("vuelos_catalogo", vuelo["id"])
    assert vuelo_actualizado["estado"] == "cancelado"

    await pb.delete_record("disrupciones", disrupcion["id"])


# ── CHK003 — los 5 tipos de cambio ──────────────────────────────────────

@pytest.mark.parametrize(
    "asunto,tipo_esperado",
    [
        ("Flight {vuelo} Cancelled", "cancelacion"),
        ("Flight {vuelo} Diverted", "desvio"),
        ("Flight {vuelo} Delayed", "retraso"),
        ("Gate change for flight {vuelo}", "cambio_puerta"),
        ("Schedule change for flight {vuelo}", "cambio_horario"),
    ],
)
async def test_deteccion_identifica_los_5_tipos_de_cambio(vuelo_factory, asunto, tipo_esperado):
    vuelo = await vuelo_factory(estado="programado", numero_vuelo=_numero_vuelo_realista())
    correo = _correo(asunto.format(vuelo=vuelo["numero_vuelo"]))

    detectado = await parsear_correo_a_disrupcion(correo)
    assert detectado is not None
    assert detectado["tipo_cambio"] == tipo_esperado
    assert detectado["vuelo_id"] == vuelo["id"]


# ── CHK008, RN-DIS-001, QP-07 ────────────────────────────────────────────

async def test_correo_sin_vuelo_reconocido_se_descarta_sin_notificar(gmail_client_falso, notification_sender_falso):
    correo = _correo("Flight ZZ9999 Cancelled", "Your flight has been cancelled.")
    cliente = gmail_client_falso([correo])

    resumen = await monitorear_correo(cliente, notification_sender_falso)
    assert resumen["disrupciones_creadas"] == 0
    assert resumen["descartados"] == 1


# ── Caso negativo: correo que no es de aerolínea ────────────────────────

async def test_correo_no_es_de_aerolinea_se_descarta_silenciosamente(gmail_client_falso, notification_sender_falso):
    correo = _correo("Tu factura mensual está lista", "Revisa tu resumen de consumo aquí.")
    cliente = gmail_client_falso([correo])

    resumen = await monitorear_correo(cliente, notification_sender_falso)
    assert resumen["disrupciones_creadas"] == 0
    assert resumen["descartados"] == 1
