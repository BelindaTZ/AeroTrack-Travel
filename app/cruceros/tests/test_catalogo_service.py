"""RF-CRU-005/006 (CU-O122/O123) — generación de catálogo (navieras/
barcos/cruceros/camarotes) + disponibilidad sintética, con doble
determinista (ver conftest.py). Forma real confirmada en vivo 2026-07-19
antes de escribir la extracción."""

from app.cruceros.services.catalogo_service import generar_catalogo

NAVIERA_REAL = {
    "company": "carnival",
    "display_name": "Carnival Cruise Line",
    "destinations": ["Western Caribbean", "Bahamas"],
}

CRUCERO_RESUMEN = {
    "cruise_id": "22078",
    "company": "carnival",
    "ship_name": "Carnival Valor",
    "departure_date": "2026-07-20T00:00:00+00:00",
    "duration": 5,
    "price": 1083,
    "currency": "AUD",
    "ports_list": [{"port": "New Orleans, Louisiana", "day": 1}],
}

CRUCERO_DETALLE = {
    "cruise_id": "22078",
    "cabin_prices_per_person": {"INTERIOR": 700.0, "BALCONY": 950.0},
}


async def test_generar_catalogo_crea_naviera_barco_crucero_y_camarotes(pb, cruisepricing_falso):
    cliente = cruisepricing_falso(
        navieras=[NAVIERA_REAL], cruceros=[CRUCERO_RESUMEN], detalles={"22078": CRUCERO_DETALLE}
    )

    resumen = await generar_catalogo(cliente, limite=1)
    assert resumen["procesados"] == 1
    assert resumen["resueltos"] == 1
    assert resumen["estado"] == "exitoso"

    naviera = await pb.get_first("navieras", 'slug_proveedor="carnival"')
    assert naviera is not None
    assert naviera["nombre"] == "Carnival Cruise Line"  # display_name real, no el slug

    barco = await pb.get_first("barcos", f'naviera_id="{naviera["id"]}" && nombre="Carnival Valor"')
    assert barco is not None

    crucero = await pb.get_first("cruceros_catalogo", 'fuente_cruise_id="22078"')
    assert crucero is not None
    assert crucero["naviera_id"] == naviera["id"]
    assert crucero["barco_id"] == barco["id"]
    assert crucero["precio_base"] == 1083

    camarotes = await pb.list_records("cruceros_camarotes_tarifa", {"filter": f'crucero_id="{crucero["id"]}"'})
    assert camarotes["totalItems"] == 2
    interior = next(c for c in camarotes["items"] if c["tipo_camarote"] == "INTERIOR")
    assert interior["precio_por_persona"] == 700.0  # precio real por camarote
    assert interior["cupos_disponibles"] == 20  # sintético, RF-CRU-006

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="crucero" && estado="exitoso"')
    assert log is not None

    for c in camarotes["items"]:
        await pb.delete_record("cruceros_camarotes_tarifa", c["id"])
    await pb.delete_record("cruceros_catalogo", crucero["id"])
    await pb.delete_record("barcos", barco["id"])
    await pb.delete_record("navieras", naviera["id"])
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_es_idempotente_no_duplica(pb, cruisepricing_falso):
    cliente = cruisepricing_falso(
        navieras=[NAVIERA_REAL], cruceros=[CRUCERO_RESUMEN], detalles={"22078": CRUCERO_DETALLE}
    )

    await generar_catalogo(cliente, limite=1)
    await generar_catalogo(cliente, limite=1)

    navieras = await pb.list_records("navieras", {"filter": 'slug_proveedor="carnival"'})
    assert navieras["totalItems"] == 1
    cruceros = await pb.list_records("cruceros_catalogo", {"filter": 'fuente_cruise_id="22078"'})
    assert cruceros["totalItems"] == 1
    crucero = cruceros["items"][0]

    camarotes = await pb.list_records("cruceros_camarotes_tarifa", {"filter": f'crucero_id="{crucero["id"]}"'})
    assert camarotes["totalItems"] == 2  # se reemplaza, no se duplica

    for c in camarotes["items"]:
        await pb.delete_record("cruceros_camarotes_tarifa", c["id"])
    await pb.delete_record("cruceros_catalogo", crucero["id"])
    barcos = await pb.list_records("barcos", {"filter": f'naviera_id="{navieras["items"][0]["id"]}"'})
    for b in barcos["items"]:
        await pb.delete_record("barcos", b["id"])
    await pb.delete_record("navieras", navieras["items"][0]["id"])
    logs = await pb.list_records(
        "sincronizaciones_log", {"filter": 'tipo_producto="crucero"', "sort": "-created", "perPage": 5}
    )
    for log in logs["items"][:2]:
        await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_falla_completa_queda_registrada_como_fallido(pb, cruisepricing_falso):
    class ClienteQueFalla(cruisepricing_falso):
        async def listar_navieras(self) -> list[dict]:
            raise ConnectionError("Cruise Pricing API no disponible (doble de prueba)")

    resumen = await generar_catalogo(ClienteQueFalla(), limite=1)
    assert resumen["estado"] == "fallido"
    assert "no disponible" in resumen["error_detalle"]

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="crucero" && estado="fallido"')
    assert log is not None
    await pb.delete_record("sincronizaciones_log", log["id"])
