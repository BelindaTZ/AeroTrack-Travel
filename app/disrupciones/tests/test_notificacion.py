import datetime

from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.disrupciones.services.notificacion_service import aplicar_precedencia, procesar_disrupcion
from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import get_pocketbase_client


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


async def _limpiar_disrupcion_y_notificaciones(disrupcion_id: str) -> None:
    notas = await moc.listar_todos("notificaciones")
    for n in [n for n in notas if n.get("disrupcion_id") == disrupcion_id]:
        await moc.eliminar("notificaciones", n["id"])
    await moc.eliminar("disrupciones", disrupcion_id)


# ── CHK004, CHK020 ───────────────────────────────────────────────────────

async def test_disrupcion_genera_notificacion_a_titular(vuelo_con_reserva_confirmada, notification_sender_falso):
    vuelo = vuelo_con_reserva_confirmada["vuelo"]
    pasajero = vuelo_con_reserva_confirmada["pasajero"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    disrupcion = await _crear_disrupcion(vuelo["id"], "api_real", "retraso")

    resultado = await procesar_disrupcion(disrupcion["id"], notification_sender_falso)
    assert resultado["notificaciones_generadas"] == 1
    assert len(notification_sender_falso.enviados) == 1
    assert notification_sender_falso.enviados[0]["canal"] == "email"

    notificacion = await DisrupcionesRepository().notificaciones_de_disrupcion_y_pasajero(
        disrupcion["id"], pasajero["id"]
    )
    notificacion = notificacion[0] if notificacion else None
    assert notificacion is not None
    assert notificacion["reserva_id"] == reserva["id"]
    assert notificacion["estado_envio"] == "enviado"

    await _limpiar_disrupcion_y_notificaciones(disrupcion["id"])


async def test_no_reenvia_a_quien_ya_fue_notificado_por_la_misma_disrupcion(
    vuelo_con_reserva_confirmada, notification_sender_falso
):
    vuelo = vuelo_con_reserva_confirmada["vuelo"]
    disrupcion = await _crear_disrupcion(vuelo["id"], "api_real", "retraso")

    await procesar_disrupcion(disrupcion["id"], notification_sender_falso)
    resultado_2 = await procesar_disrupcion(disrupcion["id"], notification_sender_falso)
    assert resultado_2["notificaciones_generadas"] == 0
    assert len(notification_sender_falso.enviados) == 1

    await _limpiar_disrupcion_y_notificaciones(disrupcion["id"])


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
    vuelo_con_reserva_confirmada, notification_sender_falso
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

    await _limpiar_disrupcion_y_notificaciones(disrupcion_correo["id"])
    await _limpiar_disrupcion_y_notificaciones(disrupcion_api["id"])


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

    facturacion_repo = FacturacionRepository()

    # Necesita un pago exitoso real detrás — paga la reserva primero
    # (admin_client pasa `_autorizado` porque es administrador).
    resp = await admin_client.post(f"/reservas/{reserva['id']}/pagar", data={"escenario": "exitoso"})
    assert resp.status_code == 303
    pago = await facturacion_repo.pago_exitoso_de_reserva(reserva["id"])
    assert pago is not None

    disrupcion = await _crear_disrupcion(vuelo["id"], "api_real", "cancelacion")
    await procesar_disrupcion(disrupcion["id"], notification_sender_falso)

    reembolsos = await moc.listar_todos("reembolsos")
    reembolso = next((r for r in reembolsos if r.get("reserva_id") == reserva["id"]), None)
    assert reembolso is not None
    assert reembolso["estado"] == "procesado"
    assert reembolso["monto"] == pago["monto"]

    await _limpiar_disrupcion_y_notificaciones(disrupcion["id"])
    await moc.eliminar("reembolsos", reembolso["id"])
    factura = await facturacion_repo.factura_de_pago(pago["id"])
    if factura is not None:
        await moc.eliminar("facturas", factura["id"])
    comisiones = await facturacion_repo.listar_comisiones()
    comision = next((c for c in comisiones if c.get("reserva_id") == reserva["id"]), None)
    if comision is not None:
        await moc.eliminar("comisiones", comision["id"])
    await moc.eliminar("pagos", pago["id"])


async def test_retraso_no_dispara_reembolso(vuelo_con_reserva_confirmada, notification_sender_falso):
    vuelo = vuelo_con_reserva_confirmada["vuelo"]
    reserva = vuelo_con_reserva_confirmada["reserva"]
    disrupcion = await _crear_disrupcion(vuelo["id"], "api_real", "retraso")

    await procesar_disrupcion(disrupcion["id"], notification_sender_falso)

    reembolsos = await moc.listar_todos("reembolsos")
    reembolso = next((r for r in reembolsos if r.get("reserva_id") == reserva["id"]), None)
    assert reembolso is None

    await _limpiar_disrupcion_y_notificaciones(disrupcion["id"])


# ── ampliación de sesión 2026-08-01 — plantilla de disrupción editable
# desde Configuración del sistema (disrupciones.plantilla_retraso) ────────

async def test_notificacion_usa_plantilla_configurada(vuelo_con_reserva_confirmada, notification_sender_falso):
    pb_client = get_pocketbase_client()
    config = await pb_client.get_first("configuracion_sistema", 'clave="disrupciones.plantilla_retraso"')
    original = config["valor"]
    await pb_client.update_record(
        "configuracion_sistema", config["id"], {"valor": "Aviso personalizado para {numero_vuelo}."}
    )
    try:
        vuelo = vuelo_con_reserva_confirmada["vuelo"]
        disrupcion = await _crear_disrupcion(vuelo["id"], "api_real", "retraso")

        await procesar_disrupcion(disrupcion["id"], notification_sender_falso)

        assert len(notification_sender_falso.enviados) == 1
        cuerpo = notification_sender_falso.enviados[0]["cuerpo"]
        assert cuerpo == f"Aviso personalizado para {vuelo['numero_vuelo']}."

        await _limpiar_disrupcion_y_notificaciones(disrupcion["id"])
    finally:
        await pb_client.update_record("configuracion_sistema", config["id"], {"valor": original})
