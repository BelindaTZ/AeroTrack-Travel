"""RF-AUT-004 (CU-O119) — generación de catálogo vía Global Rental Cars
(sub-proveedor Expedia), con doble determinista (ver conftest.py). Forma
de las tarjetas confirmada en vivo 2026-07-19 (estructura real tipo
GraphQL de Expedia, no la que sugería la doc previa a esta verificación).

Estos tests usan `fuente_por_nombre("Global Rental Cars")` real (mismo
patrón que Hoteles/Actividades/Cruceros) para las aserciones de
`sincronizaciones_log` — por eso el gate de cuota real
(`app/shared/cuota_service.hay_cupo`, ver `test_cuota_service.py` para su
prueba dedicada) se neutraliza aquí con monkeypatch: esta suite prueba el
parseo/normalización de tarjetas, no el gate, y no debe depender de cuánta
cuota real le queda a la cuenta de RapidAPI en el momento de correr."""

import app.autos.services.catalogo_service as catalogo_service
from app.autos.services.catalogo_service import generar_catalogo


async def _hay_cupo_siempre(*_args, **_kwargs) -> bool:
    return True

TARJETA_CON_PRECIO = {
    "vehicle": {
        "category": "Compact SUV",
        "description": "Opel Mokka or similar",
        "attributes": [
            {"icon": {"id": "person"}, "text": "5"},
            {"icon": {"id": "transmission"}, "text": "Manual"},
        ],
    },
    "priceSummary": {"lead": {"formattedValue": "$63"}, "total": {"formattedValue": "$778"}},
    "vendor": {"image": {"description": "Sixt"}},
    "actionableConfidenceMessages": [{"value": "Free cancellation"}, {"value": "Pay at pick-up"}],
    "detailsContext": {"carOfferToken": "token-abc-123"},
}

TARJETA_SIN_PRECIO = {
    "vehicle": {"category": "Economy", "description": "Kia Rio or similar", "attributes": []},
    "priceSummary": {"lead": {"formattedValue": None}},
    "vendor": {"image": {"description": "Hertz"}},
    "actionableConfidenceMessages": [],
    "detailsContext": {"carOfferToken": "token-sin-precio"},
}


async def test_generar_catalogo_crea_auto_desde_tarjeta_real(pb, rentalcars_falso, monkeypatch):
    monkeypatch.setattr(catalogo_service, "hay_cupo", _hay_cupo_siempre)
    cliente = rentalcars_falso(codigos={"Paris": "PAR"}, tarjetas={"PAR": [TARJETA_CON_PRECIO]})

    resumen = await generar_catalogo(cliente, ciudades=["Paris"])
    assert resumen["procesados"] == 1
    assert resumen["creados"] == 1
    assert resumen["estado"] == "exitoso"

    auto = await pb.get_first("autos_catalogo", 'fuente_oferta_ref="token-abc-123"')
    assert auto is not None
    assert auto["categoria"] == "Compact SUV"
    assert auto["modelo"] == "Opel Mokka"  # "or similar" se limpia
    assert auto["transmision"] == "Manual"
    assert auto["precio_dia"] == 63.0
    assert auto["moneda"] == "USD"
    assert auto["modalidad_pago_disponible"] == "pagar_al_recoger"  # "Pay at pick-up" presente
    assert auto["ciudad_recogida"] == "Paris"
    assert auto["aeropuerto_codigo"] == "PAR"
    assert auto["proveedor_agregador"] == "expedia"

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="auto" && estado="exitoso"')
    assert log is not None

    await pb.delete_record("autos_catalogo", auto["id"])
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_es_idempotente_reemplaza_ofertas_viejas(pb, rentalcars_falso, monkeypatch):
    monkeypatch.setattr(catalogo_service, "hay_cupo", _hay_cupo_siempre)
    cliente = rentalcars_falso(codigos={"Paris": "PAR"}, tarjetas={"PAR": [TARJETA_CON_PRECIO]})

    await generar_catalogo(cliente, ciudades=["Paris"])
    await generar_catalogo(cliente, ciudades=["Paris"])

    autos = await pb.list_records("autos_catalogo", {"filter": 'fuente_oferta_ref="token-abc-123"'})
    assert autos["totalItems"] == 1  # RN-AUT-001: snapshot reemplazado, no acumulado

    logs = await pb.list_records(
        "sincronizaciones_log", {"filter": 'tipo_producto="auto"', "sort": "-created", "perPage": 5}
    )
    for auto in autos["items"]:
        await pb.delete_record("autos_catalogo", auto["id"])
    for log in logs["items"][:2]:
        await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_sin_precio_no_crea_oferta(pb, rentalcars_falso, monkeypatch):
    """Una tarjeta sin precio real no es un error — no todas las ofertas
    del proveedor traen precio poblado."""
    monkeypatch.setattr(catalogo_service, "hay_cupo", _hay_cupo_siempre)
    cliente = rentalcars_falso(codigos={"Paris": "PAR"}, tarjetas={"PAR": [TARJETA_SIN_PRECIO]})

    resumen = await generar_catalogo(cliente, ciudades=["Paris"])
    assert resumen["procesados"] == 1
    assert resumen["creados"] == 0
    assert resumen["estado"] == "parcial"

    auto = await pb.get_first("autos_catalogo", 'fuente_oferta_ref="token-sin-precio"')
    assert auto is None

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="auto" && estado="parcial"')
    assert log is not None
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_ciudad_no_resoluble_se_omite(pb, rentalcars_falso, monkeypatch):
    monkeypatch.setattr(catalogo_service, "hay_cupo", _hay_cupo_siempre)
    cliente = rentalcars_falso(codigos={"CiudadInventada": None})

    resumen = await generar_catalogo(cliente, ciudades=["CiudadInventada"])
    assert resumen["procesados"] == 0
    assert resumen["estado"] == "parcial"

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="auto" && estado="parcial"')
    assert log is not None
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_falla_completa_queda_registrada_como_fallido(pb, rentalcars_falso, monkeypatch):
    monkeypatch.setattr(catalogo_service, "hay_cupo", _hay_cupo_siempre)

    class ClienteQueFalla(rentalcars_falso):
        async def resolver_codigo_ciudad(self, ciudad: str) -> str | None:
            raise ConnectionError("Global Rental Cars no disponible (doble de prueba)")

    resumen = await generar_catalogo(ClienteQueFalla(), ciudades=["Paris"])
    assert resumen["estado"] == "fallido"
    assert "no disponible" in resumen["error_detalle"]

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="auto" && estado="fallido"')
    assert log is not None
    await pb.delete_record("sincronizaciones_log", log["id"])
