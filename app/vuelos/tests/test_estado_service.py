import pytest

from app.vuelos.services.estado_service import EstadoInvalido, actualizar_estado


# ── RF-VUE-004 (CHK005) ────────────────────────────────────────────────────

async def test_actualizar_estado_registra_fecha_actualizacion(pb, vuelo_factory):
    vuelo = await vuelo_factory(estado="programado")

    actualizado = await actualizar_estado(vuelo["id"], "retrasado")

    assert actualizado["estado"] == "retrasado"
    assert actualizado["fecha_actualizacion_estado"] != vuelo.get("fecha_actualizacion_estado")
    assert actualizado["fecha_actualizacion_estado"]


async def test_actualizar_estado_automatico_no_marca_generado_por_manual(vuelo_factory):
    vuelo = await vuelo_factory(estado="programado", generado_por="sistema")
    actualizado = await actualizar_estado(vuelo["id"], "cancelado", origen="automatico")
    assert actualizado["generado_por"] == "sistema"


async def test_actualizar_estado_manual_marca_generado_por_manual(vuelo_factory):
    vuelo = await vuelo_factory(estado="programado", generado_por="sistema")
    actualizado = await actualizar_estado(vuelo["id"], "desviado", origen="manual")
    assert actualizado["generado_por"] == "manual"


async def test_estado_invalido_se_rechaza_sin_tocar_el_registro(pb, vuelo_factory):
    vuelo = await vuelo_factory(estado="programado")

    with pytest.raises(EstadoInvalido):
        await actualizar_estado(vuelo["id"], "en_el_limbo")

    sin_cambios = await pb.get_record("vuelos_catalogo", vuelo["id"])
    assert sin_cambios["estado"] == "programado"
