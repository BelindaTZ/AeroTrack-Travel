"""CHK004-006, CHK009-010 (RF-INT-002, RN-INT-003, CU-T37/T38)."""

import datetime


async def _crear_fuente(pb, sufijo: str) -> dict:
    admin = await pb.get_first("usuarios", 'tipo_actor="administrador"')
    return await pb.create_record(
        "fuentes_datos_externas",
        {
            "nombre": f"Fuente bitácora {sufijo}",
            "tipo_uso": "catalogo_periodico",
            "tipo_producto_alimentado": "hotel",
            "activa": True,
            "modificado_por": admin["id"],
        },
    )


def _iso(dias_atras: int = 0) -> str:
    momento = datetime.datetime.utcnow() - datetime.timedelta(days=dias_atras)
    return momento.strftime("%Y-%m-%d %H:%M:%S.000Z")


# ── CU-T37: disparar resincronización manual (ejecutado_por poblado) ────

async def test_resincronizar_fuente_catalogo_periodico_crea_log_manual(admin_client, pb):
    fuente = await _crear_fuente(pb, "resync")
    try:
        resp = await admin_client.post(f"/backoffice/integraciones/fuentes/{fuente['id']}/resincronizar")
        assert resp.status_code == 303

        log = await pb.get_first("sincronizaciones_log", f'fuente_id="{fuente["id"]}"')
        assert log is not None
        assert log["ejecutado_por"]  # poblado = corrida manual, no automática
    finally:
        logs = await pb.list_records("sincronizaciones_log", {"filter": f'fuente_id="{fuente["id"]}"'})
        for item in logs["items"]:
            await pb.delete_record("sincronizaciones_log", item["id"])
        await pb.delete_record("fuentes_datos_externas", fuente["id"])


async def test_resincronizar_fuente_regla_negocio_interna_se_rechaza(admin_client, pb):
    admin = await pb.get_first("usuarios", 'tipo_actor="administrador"')
    fuente = await pb.create_record(
        "fuentes_datos_externas",
        {"nombre": "Fuente regla interna test", "tipo_uso": "regla_negocio_interna", "activa": True, "modificado_por": admin["id"]},
    )
    try:
        resp = await admin_client.post(f"/backoffice/integraciones/fuentes/{fuente['id']}/resincronizar")
        assert resp.status_code == 303
        log = await pb.get_first("sincronizaciones_log", f'fuente_id="{fuente["id"]}"')
        assert log is None  # no crea bitácora para un tipo_uso que no admite resync
    finally:
        await pb.delete_record("fuentes_datos_externas", fuente["id"])


# ── CHK004/005: bitácora filtrable por fuente y fecha, sin botón Aplicar ──

async def test_bitacora_filtra_por_fuente_y_fecha(admin_client, pb):
    fuente_a = await _crear_fuente(pb, "filtro-a")
    fuente_b = await _crear_fuente(pb, "filtro-b")
    log_a = await pb.create_record(
        "sincronizaciones_log",
        {
            "fuente_id": fuente_a["id"], "tipo_producto": "hotel",
            "fecha_inicio": _iso(0), "fecha_fin": _iso(0),
            "estado": "exitoso", "registros_procesados": 10, "registros_nuevos": 3, "registros_actualizados": 7,
        },
    )
    log_b = await pb.create_record(
        "sincronizaciones_log",
        {
            "fuente_id": fuente_b["id"], "tipo_producto": "hotel",
            "fecha_inicio": _iso(10), "fecha_fin": _iso(10),
            "estado": "exitoso", "registros_procesados": 5, "registros_nuevos": 5, "registros_actualizados": 0,
        },
    )
    try:
        resp = await admin_client.get(f"/backoffice/integraciones/bitacora?fuente_id={fuente_a['id']}")
        assert resp.status_code == 200
        assert f"log-{log_a['id']}" in resp.text
        assert f"log-{log_b['id']}" not in resp.text

        hoy = datetime.date.today().isoformat()
        resp_fecha = await admin_client.get(f"/backoffice/integraciones/bitacora?desde={hoy}&hasta={hoy}")
        assert resp_fecha.status_code == 200
        assert f"log-{log_a['id']}" in resp_fecha.text
        assert f"log-{log_b['id']}" not in resp_fecha.text
    finally:
        await pb.delete_record("sincronizaciones_log", log_a["id"])
        await pb.delete_record("sincronizaciones_log", log_b["id"])
        await pb.delete_record("fuentes_datos_externas", fuente_a["id"])
        await pb.delete_record("fuentes_datos_externas", fuente_b["id"])


# ── CHK006/RN-INT-003: una corrida fallida no oculta la última exitosa ──

async def test_corrida_fallida_no_oculta_ultima_exitosa(admin_client, pb):
    fuente = await _crear_fuente(pb, "fallo-no-oculta")
    log_exitoso = await pb.create_record(
        "sincronizaciones_log",
        {
            "fuente_id": fuente["id"], "tipo_producto": "hotel",
            "fecha_inicio": _iso(1), "fecha_fin": _iso(1),
            "estado": "exitoso", "registros_procesados": 20, "registros_nuevos": 20, "registros_actualizados": 0,
        },
    )
    log_fallido = await pb.create_record(
        "sincronizaciones_log",
        {
            "fuente_id": fuente["id"], "tipo_producto": "hotel",
            "fecha_inicio": _iso(0), "fecha_fin": _iso(0),
            "estado": "fallido", "registros_procesados": 0, "registros_nuevos": 0, "registros_actualizados": 0,
            "error_detalle": "rate limit",
        },
    )
    try:
        resp = await admin_client.get(f"/backoffice/integraciones/bitacora?fuente_id={fuente['id']}")
        assert resp.status_code == 200
        # ambas corridas visibles — la fallida no reemplaza ni oculta la exitosa
        assert f"log-{log_exitoso['id']}" in resp.text
        assert f"log-{log_fallido['id']}" in resp.text
    finally:
        await pb.delete_record("sincronizaciones_log", log_exitoso["id"])
        await pb.delete_record("sincronizaciones_log", log_fallido["id"])
        await pb.delete_record("fuentes_datos_externas", fuente["id"])
