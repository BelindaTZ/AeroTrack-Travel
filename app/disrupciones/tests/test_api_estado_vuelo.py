import datetime

from app.disrupciones.integrations.flight_status_client import AviationStackClient
from app.disrupciones.services.api_estado_vuelo_service import consultar_estados_cercanos


def _fecha_cercana(horas: int = 24) -> str:
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=horas)).strftime(
        "%Y-%m-%d %H:%M:%S.000Z"
    )


# ── CHK001, CHK017 ──────────────────────────────────────────────────────

async def test_disrupcion_creada_por_api_real_cuando_estado_difiere(
    pb, vuelo_factory, flight_status_falso, notification_sender_falso
):
    vuelo = await vuelo_factory(estado="programado", fecha_salida=_fecha_cercana())
    cliente = flight_status_falso(
        disponible=True,
        respuestas={vuelo["numero_vuelo"]: {"estado_api": "retrasado", "retraso_minutos": 45, "nueva_hora_llegada": None}},
    )

    resumen = await consultar_estados_cercanos(cliente, notification_sender_falso)
    assert resumen["disrupciones_creadas"] >= 1
    assert resumen["degradado"] is False

    disrupcion = await pb.get_first("disrupciones", f'vuelo_id="{vuelo["id"]}" && fuente_deteccion="api_real"')
    assert disrupcion is not None
    assert disrupcion["tipo_cambio"] == "retraso"
    assert disrupcion["estado"] == "activa"

    vuelo_actualizado = await pb.get_record("vuelos_catalogo", vuelo["id"])
    assert vuelo_actualizado["estado"] == "retrasado"

    await pb.delete_record("disrupciones", disrupcion["id"])


# ── CHK012, CHK014, RNF-DIS-001 ────────────────────────────────────────

async def test_degradacion_no_falla_y_continua(vuelo_factory, flight_status_falso, notification_sender_falso):
    await vuelo_factory(estado="programado", fecha_salida=_fecha_cercana())
    cliente = flight_status_falso(disponible=False)

    resumen = await consultar_estados_cercanos(cliente, notification_sender_falso)
    assert resumen["degradado"] is True
    assert resumen["disrupciones_creadas"] == 0


async def test_falla_puntual_en_un_vuelo_no_interrumpe_el_resto(
    pb, vuelo_factory, flight_status_falso, notification_sender_falso
):
    vuelo_ok = await vuelo_factory(estado="programado", fecha_salida=_fecha_cercana())
    vuelo_falla = await vuelo_factory(estado="programado", fecha_salida=_fecha_cercana())

    class ClienteConUnaFalla(flight_status_falso):
        async def consultar_estado(self, numero_vuelo, fecha):
            if numero_vuelo == vuelo_falla["numero_vuelo"]:
                raise TimeoutError("caída puntual (doble de prueba)")
            return await super().consultar_estado(numero_vuelo, fecha)

    cliente = ClienteConUnaFalla(
        disponible=True,
        respuestas={vuelo_ok["numero_vuelo"]: {"estado_api": "cancelado", "retraso_minutos": None, "nueva_hora_llegada": None}},
    )

    resumen = await consultar_estados_cercanos(cliente, notification_sender_falso)
    assert resumen["degradado"] is True
    assert resumen["disrupciones_creadas"] >= 1

    disrupcion = await pb.get_first("disrupciones", f'vuelo_id="{vuelo_ok["id"]}"')
    assert disrupcion is not None
    assert disrupcion["tipo_cambio"] == "cancelacion"
    await pb.delete_record("disrupciones", disrupcion["id"])


# ── CHK015, RNF-DIS-002 ─────────────────────────────────────────────────

async def test_timeout_se_lee_de_configuracion_sistema_no_hardcodeado(pb):
    config = await pb.get_first("configuracion_sistema", 'clave="api_estado_vuelo.timeout_segundos"')
    assert config is not None

    cliente = AviationStackClient()
    valores = await cliente._config()
    assert valores["api_estado_vuelo.timeout_segundos"] == config["valor"]


# ── Caso negativo ────────────────────────────────────────────────────────

async def test_mismo_estado_no_genera_disrupcion(pb, vuelo_factory, flight_status_falso, notification_sender_falso):
    vuelo = await vuelo_factory(estado="programado", fecha_salida=_fecha_cercana())
    cliente = flight_status_falso(
        disponible=True,
        respuestas={vuelo["numero_vuelo"]: {"estado_api": "programado", "retraso_minutos": None, "nueva_hora_llegada": None}},
    )

    resumen = await consultar_estados_cercanos(cliente, notification_sender_falso)
    assert resumen["disrupciones_creadas"] == 0

    disrupcion = await pb.get_first("disrupciones", f'vuelo_id="{vuelo["id"]}"')
    assert disrupcion is None
