"""RF-ACT-004/005/006 (CU-O120/O121) — generación de catálogo + reseñas +
disponibilidad sintética, con doble determinista (ver conftest.py). Forma
de las tarjetas/detalle confirmada en vivo 2026-07-19 ANTES de escribir la
extracción (a diferencia de Hoteles/Autos)."""

from app.actividades.services.catalogo_service import generar_catalogo

TARJETA = {
    "trackingKey": '{"prc":19.82,"cur":"USD","lid":11475917,"br":4.2,"rc":301}',
    "cardTitle": {"string": "1. Paris Seine River Sightseeing Guided Cruise"},
    "primaryInfo": {"text": "Sightseeing Cruises"},
    "cardPhoto": {"sizes": {"urlTemplate": "https://example.com/foto.jpg"}},
}

DETALLE = {
    "name": "Paris Seine River Sightseeing Guided Cruise Vedettes du Pont Neuf",
    "description": "Descripción real de la actividad",
    "rating": 4.2,
    "num_reviews": 1078,
    "address_obj": {"city": "Paris", "country": "France"},
    "category": {"key": "activity", "name": "Activity"},
    "reviews": [
        {
            "author": "Nomad36842900415",
            "rating": "5",
            "summary": "Absolutely the best time!",
            "published_date": "2026-07-18T11:15:18-04:00",
        }
    ],
}


async def test_generar_catalogo_crea_actividad_resena_y_disponibilidad(pb, traveladvisor_falso):
    cliente = traveladvisor_falso(
        geo_ids={"Paris": 187147},
        tarjetas={187147: [TARJETA]},
        detalles={"11475917": DETALLE},
    )

    resumen = await generar_catalogo(cliente, ciudades=["Paris"], max_actividades_por_ciudad=1)
    assert resumen["procesados"] == 1
    assert resumen["resueltos"] == 1
    assert resumen["estado"] == "exitoso"

    actividad = await pb.get_first("actividades_catalogo", 'fuente_content_id="11475917"')
    assert actividad is not None
    assert actividad["nombre"] == DETALLE["name"]  # nombre limpio del detalle, sin el prefijo "1. " del listado
    assert actividad["ciudad"] == "Paris"
    assert actividad["categoria"] == "Sightseeing Cruises"  # primaryInfo, más específico que category.name
    assert actividad["precio_desde"] == 19.82

    resenas = await pb.list_records("actividades_resenas", {"filter": f'actividad_id="{actividad["id"]}"'})
    assert resenas["totalItems"] == 1
    assert resenas["items"][0]["autor"] == "Nomad36842900415"

    horarios = await pb.list_records(
        "actividades_horarios", {"filter": f'actividad_id="{actividad["id"]}"', "perPage": 100}
    )
    assert horarios["totalItems"] == 14 * 3  # dias_adelante default * horarios_por_dia default
    assert horarios["items"][0]["cupos_disponibles"] == 15
    assert horarios["items"][0]["precio"] == 19.82

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="actividad" && estado="exitoso"')
    assert log is not None

    for h in horarios["items"]:
        await pb.delete_record("actividades_horarios", h["id"])
    for r in resenas["items"]:
        await pb.delete_record("actividades_resenas", r["id"])
    await pb.delete_record("actividades_catalogo", actividad["id"])
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_es_idempotente_no_duplica_actividad(pb, traveladvisor_falso):
    cliente = traveladvisor_falso(
        geo_ids={"Paris": 187147}, tarjetas={187147: [TARJETA]}, detalles={"11475917": DETALLE}
    )

    await generar_catalogo(cliente, ciudades=["Paris"], max_actividades_por_ciudad=1)
    await generar_catalogo(cliente, ciudades=["Paris"], max_actividades_por_ciudad=1)

    actividades = await pb.list_records("actividades_catalogo", {"filter": 'fuente_content_id="11475917"'})
    assert actividades["totalItems"] == 1
    actividad = actividades["items"][0]

    horarios = await pb.list_records(
        "actividades_horarios", {"filter": f'actividad_id="{actividad["id"]}"', "perPage": 200}
    )
    assert horarios["totalItems"] == 14 * 3  # se reemplaza, no se duplica

    resenas = await pb.list_records("actividades_resenas", {"filter": f'actividad_id="{actividad["id"]}"'})
    for h in horarios["items"]:
        await pb.delete_record("actividades_horarios", h["id"])
    for r in resenas["items"]:
        await pb.delete_record("actividades_resenas", r["id"])
    await pb.delete_record("actividades_catalogo", actividad["id"])
    logs = await pb.list_records(
        "sincronizaciones_log", {"filter": 'tipo_producto="actividad"', "sort": "-created", "perPage": 5}
    )
    for log in logs["items"][:2]:
        await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_sin_lid_en_tracking_key_no_crea_nada(pb, traveladvisor_falso):
    tarjeta_sin_lid = {"trackingKey": '{"prc":10.0,"cur":"USD"}', "primaryInfo": {"text": "Tours"}}
    cliente = traveladvisor_falso(geo_ids={"Paris": 187147}, tarjetas={187147: [tarjeta_sin_lid]})

    resumen = await generar_catalogo(cliente, ciudades=["Paris"], max_actividades_por_ciudad=1)
    assert resumen["procesados"] == 1
    assert resumen["resueltos"] == 0
    assert resumen["estado"] == "parcial"

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="actividad" && estado="parcial"')
    assert log is not None
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_ciudad_no_resoluble_se_omite(pb, traveladvisor_falso):
    cliente = traveladvisor_falso(geo_ids={"CiudadInventada": None})

    resumen = await generar_catalogo(cliente, ciudades=["CiudadInventada"], max_actividades_por_ciudad=1)
    assert resumen["procesados"] == 0
    assert resumen["estado"] == "parcial"

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="actividad" && estado="parcial"')
    assert log is not None
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_generar_catalogo_falla_completa_queda_registrada_como_fallido(pb, traveladvisor_falso):
    class ClienteQueFalla(traveladvisor_falso):
        async def resolver_geo_id(self, ciudad: str) -> int | None:
            raise ConnectionError("Travel Advisor no disponible (doble de prueba)")

    resumen = await generar_catalogo(ClienteQueFalla(), ciudades=["Paris"], max_actividades_por_ciudad=1)
    assert resumen["estado"] == "fallido"
    assert "no disponible" in resumen["error_detalle"]

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="actividad" && estado="fallido"')
    assert log is not None
    await pb.delete_record("sincronizaciones_log", log["id"])
