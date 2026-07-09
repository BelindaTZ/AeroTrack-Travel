import asyncio

from app.vuelos.services.cupo_service import verificar_y_reservar_cupo


# ── RF-VUE-005 (CHK006) ────────────────────────────────────────────────────

async def test_cupo_disponible_decrementa_y_confirma(pb, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=5)

    resultado = await verificar_y_reservar_cupo(tarifa["id"])
    assert resultado is True

    actualizada = await pb.get_record("tarifas_vuelo", tarifa["id"])
    assert actualizada["cupos_disponibles"] == 4


async def test_cupo_cero_no_decrementa_y_responde_sin_disponibilidad(pb, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=0)

    resultado = await verificar_y_reservar_cupo(tarifa["id"])
    assert resultado is False

    sin_cambios = await pb.get_record("tarifas_vuelo", tarifa["id"])
    assert sin_cambios["cupos_disponibles"] == 0


# ── RNF-VUE-003 / RN-VUE-004 (CHK012, CHK017) ─────────────────────────────

async def test_concurrencia_nunca_vende_mas_cupo_del_disponible(pb, vuelo_factory, tarifa_factory):
    vuelo = await vuelo_factory()
    cupo_inicial = 20
    tarifa = await tarifa_factory(vuelo["id"], cupos_disponibles=cupo_inicial)

    resultados = await asyncio.gather(
        *[verificar_y_reservar_cupo(tarifa["id"]) for _ in range(50)]
    )

    exitosos = sum(1 for r in resultados if r is True)
    fallidos = sum(1 for r in resultados if r is False)
    assert exitosos == cupo_inicial
    assert fallidos == 50 - cupo_inicial

    final = await pb.get_record("tarifas_vuelo", tarifa["id"])
    assert final["cupos_disponibles"] == 0  # nunca negativo, nunca por debajo de cero
