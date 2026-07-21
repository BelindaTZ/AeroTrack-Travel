"""Test de app/shared/cuota_service.py — gate de cuota mensual real
(RapidAPI Basic: HotelLens/Global Rental Cars 100/mes, Travel Advisor
500/mes). Usa la fuente real "HotelLens" (ya sembrada por
scripts/seed_fuentes_datos_externas.py) y filas desechables de
sincronizaciones_log — sin llamar ninguna API externa."""

import datetime

from app.shared.cuota_service import (
    cupo_diario_disponible,
    hay_cupo,
    registrar_uso_diario,
    unidades_usadas_este_mes,
)


async def _crear_log(pb, fuente_id: str, unidades: int) -> str:
    ahora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    log = await pb.create_record(
        "sincronizaciones_log",
        {
            "fuente_id": fuente_id,
            "tipo_producto": "hotel",
            "fecha_inicio": ahora,
            "fecha_fin": ahora,
            "estado": "exitoso",
            "unidades_cuota_consumidas": unidades,
        },
    )
    return log["id"]


async def test_hay_cupo_sin_techo_mensual_siempre_true(pb):
    # cuota_mensual=None (ej. Cruise Pricing) — nunca gatea.
    assert await hay_cupo("id-inexistente", None, ya_gastadas_en_esta_corrida=0) is True


async def test_hay_cupo_con_margen_disponible(pb):
    fuente = await pb.get_first("fuentes_datos_externas", 'nombre="HotelLens"')
    assert fuente is not None
    baseline = await unidades_usadas_este_mes(fuente["id"])
    log_id = await _crear_log(pb, fuente["id"], unidades=5)
    try:
        # techo bien por encima de lo ya consumido (incluyendo esta fila) -> hay cupo
        cuota_holgada = baseline + 5 + 50
        assert await hay_cupo(fuente["id"], cuota_holgada, ya_gastadas_en_esta_corrida=0) is True
    finally:
        await pb.delete_record("sincronizaciones_log", log_id)


async def test_hay_cupo_sin_margen_disponible(pb):
    fuente = await pb.get_first("fuentes_datos_externas", 'nombre="HotelLens"')
    assert fuente is not None
    baseline = await unidades_usadas_este_mes(fuente["id"])
    log_id = await _crear_log(pb, fuente["id"], unidades=5)
    try:
        # techo igual a lo ya consumido -> con margen 0.85 no alcanza -> sin cupo
        cuota_ajustada = baseline + 5
        assert await hay_cupo(fuente["id"], cuota_ajustada, ya_gastadas_en_esta_corrida=0) is False
    finally:
        await pb.delete_record("sincronizaciones_log", log_id)


async def test_hay_cupo_considera_lo_gastado_en_la_corrida_actual(pb):
    fuente = await pb.get_first("fuentes_datos_externas", 'nombre="HotelLens"')
    assert fuente is not None
    baseline = await unidades_usadas_este_mes(fuente["id"])
    margen = 0.85
    # `cuota` elegido para que el umbral efectivo (cuota*margen) quede
    # exactamente 5 unidades por encima de lo ya consumido, sin importar
    # cuánto sea ese consumo real (evita que el test dependa del estado
    # ambiental de cuota — HotelLens ya tiene consumo real registrado).
    cuota = (baseline + 5) / margen

    # nada gastado en esta corrida todavía -> dentro del margen -> hay cupo
    assert await hay_cupo(fuente["id"], cuota, ya_gastadas_en_esta_corrida=0) is True
    # 9 llamadas en esta corrida > margen de 5 -> sin cupo
    assert await hay_cupo(fuente["id"], cuota, ya_gastadas_en_esta_corrida=9) is False


# ── Gate de cuota DIARIA (Places/Geocoding/Routes de Google Cloud) ──


async def _admin_id(pb) -> str:
    admin = await pb.get_first("usuarios", 'tipo_actor="administrador"')
    assert admin is not None
    return admin["id"]


async def _sembrar_config(pb, clave: str, valor: str) -> str:
    registro = await pb.create_record(
        "configuracion_sistema",
        {"clave": clave, "valor": valor, "categoria": "google_apis", "descripcion": "test",
         "modificado_por": await _admin_id(pb)},
    )
    return registro["id"]


async def test_cupo_diario_disponible_sin_limite_configurado_siempre_true(pb):
    # ningún prefijo.limite_diario sembrado -> sin gate, siempre True
    assert await cupo_diario_disponible("prefijo_inexistente_test") is True


async def test_cupo_diario_disponible_dentro_del_margen(pb):
    prefijo = "test_cuota_diaria.dentro_margen"
    hoy = datetime.date.today().isoformat()
    ids = [
        await _sembrar_config(pb, f"{prefijo}.limite_diario", "100"),
        await _sembrar_config(pb, f"{prefijo}.usadas_dia", "10"),
        await _sembrar_config(pb, f"{prefijo}.periodo_actual", hoy),
    ]
    try:
        assert await cupo_diario_disponible(prefijo) is True
    finally:
        for i in ids:
            await pb.delete_record("configuracion_sistema", i)


async def test_cupo_diario_disponible_fuera_del_margen(pb):
    prefijo = "test_cuota_diaria.fuera_margen"
    hoy = datetime.date.today().isoformat()
    ids = [
        await _sembrar_config(pb, f"{prefijo}.limite_diario", "100"),
        await _sembrar_config(pb, f"{prefijo}.usadas_dia", "90"),  # > 100*0.85=85
        await _sembrar_config(pb, f"{prefijo}.periodo_actual", hoy),
    ]
    try:
        assert await cupo_diario_disponible(prefijo) is False
    finally:
        for i in ids:
            await pb.delete_record("configuracion_sistema", i)


async def test_cupo_diario_disponible_resetea_al_cambiar_el_dia(pb):
    prefijo = "test_cuota_diaria.reset_dia"
    ids = [
        await _sembrar_config(pb, f"{prefijo}.limite_diario", "100"),
        await _sembrar_config(pb, f"{prefijo}.usadas_dia", "99"),  # agotado si no resetea
        await _sembrar_config(pb, f"{prefijo}.periodo_actual", "2000-01-01"),  # fecha vieja
    ]
    try:
        assert await cupo_diario_disponible(prefijo) is True  # cambió el día -> resetea a 0

        usadas_reg = await pb.get_first("configuracion_sistema", f'clave="{prefijo}.usadas_dia"')
        assert usadas_reg["valor"] == "0"
        periodo_reg = await pb.get_first("configuracion_sistema", f'clave="{prefijo}.periodo_actual"')
        assert periodo_reg["valor"] == datetime.date.today().isoformat()
    finally:
        for i in ids:
            await pb.delete_record("configuracion_sistema", i)


async def test_registrar_uso_diario_incrementa_contador(pb):
    prefijo = "test_cuota_diaria.incrementa"
    id_usadas = await _sembrar_config(pb, f"{prefijo}.usadas_dia", "5")
    try:
        await registrar_uso_diario(prefijo)
        registro = await pb.get_first("configuracion_sistema", f'clave="{prefijo}.usadas_dia"')
        assert registro["valor"] == "6"
    finally:
        await pb.delete_record("configuracion_sistema", id_usadas)
