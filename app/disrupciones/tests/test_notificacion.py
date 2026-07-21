import datetime

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.disrupciones.services.notificacion_service import aplicar_precedencia, procesar_disrupcion


def _ahora_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


async def _crear_disrupcion(vuelo_id: str, fuente: str, tipo_cambio: str = "retraso") -> dict:
    repo = DisrupcionesRepository()
    return await repo.crear_disrupcion(
        {
            "vuelo_id": vuelo_id,
            "fuente_deteccion": fuente,
            "tipo_cambio": tipo_cambio,
            "estado": "activa",
            "detalle": "prueba",
            "fecha_deteccion": _ahora_iso(),
        }
    )


async def _limpiar_disrupcion_y_notificaciones(pb, disrupcion_id: str) -> None:
    notas = await pb.list_records("notificaciones", {"filter": f'disrupcion_id="{disrupcion_id}"'})
    for n in notas["items"]:
        await pb.delete_record("notificaciones", n["id"])
    await pb.delete_record("disrupciones", disrupcion_id)


# ── CHK004, CHK020 ───────────────────────────────────────────────────────

async def test_disrupcion_genera_notificacion_a_titular(pb, vuelo_con_reserva_confirmada, notification_sender_falso):
    vuelo = vuelo_con_reserva_confirmada["vuelo"]
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    disrupcion = await _crear_disrupcion(vuelo["id"], "api_real", "retraso")

    resultado = await procesar_disrupcion(disrupcion["id"], notification_sender_falso)
    assert resultado["notificaciones_generadas"] == 1
    assert len(notification_sender_falso.enviados) == 1
    assert notification_sender_falso.enviados[0]["canal"] == "email"

    notificacion = await pb.get_first(
        "notificaciones", f'disrupcion_id="{disrupcion["id"]}" && pasajero_id="{pasajero["id"]}"'
    )
    assert notificacion is not None
    assert notificacion["reserva_id"] == reserva["id"]
    assert notificacion["estado_envio"] == "enviado"

    await _limpiar_disrupcion_y_notificaciones(pb, disrupcion["id"])


async def test_no_reenvia_a_quien_ya_fue_notificado_por_la_misma_disrupcion(
    pb, vuelo_con_reserva_confirmada, notification_sender_falso
):
    vuelo = vuelo_con_reserva_confirmada["vuelo"]
    disrupcion = await _crear_disrupcion(vuelo["id"], "api_real", "retraso")

    await procesar_disrupcion(disrupcion["id"], notification_sender_falso)
    resultado_2 = await procesar_disrupcion(disrupcion["id"], notification_sender_falso)
    assert resultado_2["notificaciones_generadas"] == 0
    assert len(notification_sender_falso.enviados) == 1

    await _limpiar_disrupcion_y_notificaciones(pb, disrupcion["id"])


# ── CHK009, RN-DIS-002, QP-02 — precedencia y deduplicación ─────────────

def test_aplicar_precedencia_es_funcion_pura():
    disrupciones = [
        {"id": "1", "vuelo_id": "V1", "tipo_cambio": "retraso", "fuente_deteccion": "monitor_correo"},
        {"id": "2", "vuelo_id": "V1", "tipo_cambio": "retraso", "fuente_deteccion": "api_real"},
        {"id": "3", "vuelo_id": "V1", "tipo_cambio": "retraso", "fuente_deteccion": "simulador_estadistico"},
        {"id": "4", "vuelo_id": "V2", "tipo_cambio": "cancelacion", "fuente_deteccion": "monitor_correo"},
    ]
    ganadoras = aplicar_precedencia(disrupciones)
    ids_ganadores = {d["id"] for d in ganadoras}
    assert ids_ganadores == {"2", "4"}  # api_real gana sobre monitor_correo/simulador para V1


async def test_dos_fuentes_mismo_cambio_generan_una_sola_notificacion(
    pb, vuelo_con_reserva_confirmada, notification_sender_falso
):
    vuelo = vuelo_con_reserva_confirmada["vuelo"]
    disrupcion_correo = await _crear_disrupcion(vuelo["id"], "monitor_correo", "retraso")
    disrupcion_api = await _crear_disrupcion(vuelo["id"], "api_real", "retraso")

    # La de menor precedencia (monitor_correo) cede — no genera notificación.
    resultado_correo = await procesar_disrupcion(disrupcion_correo["id"], notification_sender_falso)
    assert resultado_correo["notificaciones_generadas"] == 0

    # La de mayor precedencia (api_real) sí notifica.
    resultado_api = await procesar_disrupcion(disrupcion_api["id"], notification_sender_falso)
    assert resultado_api["notificaciones_generadas"] == 1
    assert len(notification_sender_falso.enviados) == 1

    await _limpiar_disrupcion_y_notificaciones(pb, disrupcion_correo["id"])
    await _limpiar_disrupcion_y_notificaciones(pb, disrupcion_api["id"])


# ── CHK005, CHK010, RN-DIS-003, QP-12 — reembolso condicionado ──────────

async def test_cancelacion_dispara_reembolso_real(
    admin_client, pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory, notification_sender_falso
):
    _, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory(estado="programado")
    nivel_flex = await pb.get_first("niveles_tarifa", 'nombre="Flex"')  # 100% de reembolso
    tarifa = await tarifa_factory(vuelo["id"], nivel_tarifa_id=nivel_flex["id"], precio_final=250.0)
    reserva = await reserva_factory(
        pasajero["id"], vuelo["id"], tarifa["id"], estado="pendiente_pago", total_pagar=250.0
    )

    # Necesita un pago exitoso real detrás — paga la reserva primero
    # (admin_client pasa `_autorizado` porque es administrador).
    resp = await admin_client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303
    pago = await pb.get_first("pagos", f'reserva_id="{reserva["id"]}" && estado="exitoso"')
    assert pago is not None

    disrupcion = await _crear_disrupcion(vuelo["id"], "api_real", "cancelacion")
    await procesar_disrupcion(disrupcion["id"], notification_sender_falso)

    reembolso = await pb.get_first("reembolsos", f'reserva_id="{reserva["id"]}"')
    assert reembolso is not None
    assert reembolso["estado"] == "procesado"
    assert reembolso["monto"] == pago["monto"]

    await _limpiar_disrupcion_y_notificaciones(pb, disrupcion["id"])
    await pb.delete_record("reembolsos", reembolso["id"])
    factura = await pb.get_first("facturas", f'pago_id="{pago["id"]}"')
    if factura is not None:
        await pb.delete_record("facturas", factura["id"])
    comision = await pb.get_first("comisiones", f'reserva_id="{reserva["id"]}"')
    if comision is not None:
        await pb.delete_record("comisiones", comision["id"])
    await pb.delete_record("pagos", pago["id"])


async def test_retraso_no_dispara_reembolso(pb, vuelo_con_reserva_confirmada, notification_sender_falso):
    vuelo = vuelo_con_reserva_confirmada["vuelo"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    disrupcion = await _crear_disrupcion(vuelo["id"], "api_real", "retraso")

    await procesar_disrupcion(disrupcion["id"], notification_sender_falso)

    reembolso = await pb.get_first("reembolsos", f'reserva_id="{reserva["id"]}"')
    assert reembolso is None

    await _limpiar_disrupcion_y_notificaciones(pb, disrupcion["id"])
