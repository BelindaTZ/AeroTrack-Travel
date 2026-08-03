"""Tests de app/vuelos/services/enriquecimiento_service.py — dobles
deterministas de AeroDataBox/Google Flights (ver conftest.py), sin
llamada real. Fecha fija 2027-01-01 (mismo default que `vuelo_factory` de
la raíz del repo) para no depender de la hora real del día — el test
`test_vuelos_generados_por_sistema_nacen_programados` ya mostró que usar
"hoy" real puede ser flaky según a qué hora del día corra la suite."""

import datetime

from app.vuelos.services.enriquecimiento_service import (
    enriquecer_con_aerodatabox,
    enriquecer_con_google_flights,
)
from app.vuelos.repositories.vuelos_repo import VuelosRepository

FECHA_TEST = datetime.date(2027, 1, 1)
FECHA_TEST_ISO = "2027-01-01"


async def test_enriquecer_con_aerodatabox_reemplaza_datos_sinteticos(pb, vuelo_factory, aerodatabox_falso):
    vuelo = await vuelo_factory(
        origen_codigo="ATL", destino_codigo="JFK", fecha_salida=FECHA_TEST_ISO,
        numero_vuelo="SINT001", hora_salida_programada="06:00",
    )

    cliente = aerodatabox_falso(
        salidas_por_hub={
            "ATL": [
                {
                    "numero_vuelo": "DL466",
                    "destino_codigo": "JFK",
                    "avion_modelo": "Boeing 757",
                    "hora_salida_local": "07:15",
                }
            ]
        }
    )

    resumen = await enriquecer_con_aerodatabox(cliente, hoy=FECHA_TEST, hubs=["ATL"])
    assert resumen["actualizados"] == 1
    assert resumen["estado"] == "exitoso"

    vuelo_actualizado = await pb.get_record("vuelos_catalogo", vuelo["id"])
    assert vuelo_actualizado["numero_vuelo"] == "DL466"
    assert vuelo_actualizado["avion_modelo"] == "Boeing 757"
    assert vuelo_actualizado["hora_salida_programada"] == "07:15"
    assert vuelo_actualizado["generado_por"] == "sistema_api_real"

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="vuelo" && estado="exitoso"')
    assert log is not None
    await pb.delete_record("sincronizaciones_log", log["id"])


async def test_enriquecer_con_aerodatabox_ignora_destinos_fuera_del_universo(pb, vuelo_factory, aerodatabox_falso):
    await vuelo_factory(origen_codigo="ATL", destino_codigo="JFK", fecha_salida=FECHA_TEST_ISO)

    cliente = aerodatabox_falso(
        salidas_por_hub={
            "ATL": [
                {"numero_vuelo": "DL999", "destino_codigo": "XYZ", "avion_modelo": "", "hora_salida_local": None}
            ]
        }
    )

    resumen = await enriquecer_con_aerodatabox(cliente, hoy=FECHA_TEST, hubs=["ATL"])
    assert resumen["actualizados"] == 0  # XYZ no está en el universo curado, se ignora sin romper

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="vuelo" && estado="parcial"')
    if log:
        await pb.delete_record("sincronizaciones_log", log["id"])


async def test_enriquecer_con_google_flights_actualiza_precio_real(pb, vuelo_factory, tarifa_factory, google_flights_falso):
    vuelo = await vuelo_factory(
        origen_codigo="ATL", destino_codigo="JFK", fecha_salida=FECHA_TEST_ISO,
        numero_vuelo="DL466", precio_base=100.0,
    )
    tarifa = await tarifa_factory(vuelo["id"], precio_final=100.0)
    await pb.update_record("tarifas_vuelo", tarifa["id"], {"clase_cabina": "economy"})

    cliente = google_flights_falso(
        resultados_por_ruta={
            ("ATL", "JFK"): {
                "vuelos": [
                    {
                        "numero_vuelo": "DL466",
                        "precio": 134.0,
                        "emisiones_co2_kg": 92.0,
                        "fuente_busqueda_ref": "tok123",
                        "detalles_extra": {"legroom": "31 in"},
                    }
                ],
                "predicciones": {
                    "precio_minimo_historico": 94.0,
                    "nivel_precio": "typical",
                    "rango_tipico_min": 75.0,
                    "rango_tipico_max": 155.0,
                    "historico_precios": [],
                },
            }
        }
    )

    resumen = await enriquecer_con_google_flights(cliente, hoy=FECHA_TEST, rutas=[("ATL", "JFK")])
    # 3 clases consultadas (economy/business/first, RF-VUE-010) — la misma
    # respuesta enlatada del doble aplica a las 3, así que actualiza economy
    # y CREA 2 tarifas premium nuevas (business/first) -> 3 "actualizados".
    assert resumen["actualizados"] == 3
    assert resumen["estado"] == "exitoso"

    vuelo_actualizado = await pb.get_record("vuelos_catalogo", vuelo["id"])
    assert vuelo_actualizado["precio_base"] == 134.0
    assert vuelo_actualizado["emisiones_co2_kg"] == 92.0
    assert vuelo_actualizado["fuente_busqueda_ref"] == "tok123"

    tarifa_actualizada = await pb.get_record("tarifas_vuelo", tarifa["id"])
    assert tarifa_actualizada["precio_final"] == 134.0

    prediccion = await pb.get_first(
        "predicciones_precio_ruta",
        f'origen_codigo="ATL" && destino_codigo="JFK" && fecha_objetivo ~ "{FECHA_TEST_ISO}"',
    )
    assert prediccion is not None
    assert prediccion["precio_minimo_historico"] == 94.0
    assert prediccion["precio_predicho"] == 115.0  # (75+155)/2, heurística propia, no viene de la API
    assert prediccion["tendencia"] == "estable"  # nivel_precio="typical"

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="vuelo" && estado="exitoso"')
    await pb.delete_record("predicciones_precio_ruta", prediccion["id"])
    if log:
        await pb.delete_record("sincronizaciones_log", log["id"])
    for premium in (await pb.list_records(
        "tarifas_vuelo", {"filter": f'vuelo_id="{vuelo["id"]}" && (clase_cabina="business" || clase_cabina="first")'}
    ))["items"]:
        await pb.delete_record("tarifas_vuelo", premium["id"])


async def test_enriquecer_con_google_flights_crea_tarifas_premium_con_nivel_flex(
    pb, vuelo_factory, tarifa_factory, google_flights_falso
):
    """RF-VUE-010 (CU-O114) — Business/First se crean con precio real de
    Google Flights, siempre bajo el nivel Flex (RN confirmada: cabina
    premium = condiciones de cambio/reembolso flexibles, nunca Light/Standard)."""
    vuelo = await vuelo_factory(
        origen_codigo="ATL", destino_codigo="JFK", fecha_salida=FECHA_TEST_ISO,
        numero_vuelo="DL466", precio_base=100.0,
    )
    tarifa_economy = await tarifa_factory(vuelo["id"], precio_final=100.0)
    await pb.update_record("tarifas_vuelo", tarifa_economy["id"], {"clase_cabina": "economy"})
    nivel_flex = await pb.get_first("niveles_tarifa", 'nombre="Flex"')

    cliente = google_flights_falso(
        resultados_por_ruta={
            ("ATL", "JFK", "economy"): {
                "vuelos": [{"numero_vuelo": "DL466", "precio": 134.0, "emisiones_co2_kg": None,
                            "fuente_busqueda_ref": None, "detalles_extra": None}],
                "predicciones": None,
            },
            ("ATL", "JFK", "business"): {
                "vuelos": [{"numero_vuelo": "DL466", "precio": 410.0, "emisiones_co2_kg": None,
                            "fuente_busqueda_ref": None, "detalles_extra": None}],
                "predicciones": None,
            },
            ("ATL", "JFK", "first"): {
                "vuelos": [{"numero_vuelo": "DL466", "precio": 780.0, "emisiones_co2_kg": None,
                            "fuente_busqueda_ref": None, "detalles_extra": None}],
                "predicciones": None,
            },
        }
    )

    resumen = await enriquecer_con_google_flights(cliente, hoy=FECHA_TEST, rutas=[("ATL", "JFK")])
    assert resumen["actualizados"] == 3

    tarifa_business = await pb.get_first(
        "tarifas_vuelo", f'vuelo_id="{vuelo["id"]}" && clase_cabina="business"'
    )
    tarifa_first = await pb.get_first(
        "tarifas_vuelo", f'vuelo_id="{vuelo["id"]}" && clase_cabina="first"'
    )
    assert tarifa_business is not None and tarifa_business["precio_final"] == 410.0
    assert tarifa_business["nivel_tarifa_id"] == nivel_flex["id"]
    assert tarifa_first is not None and tarifa_first["precio_final"] == 780.0
    assert tarifa_first["nivel_tarifa_id"] == nivel_flex["id"]
    # precio_base del vuelo (economy) no debe contaminarse con precios premium
    vuelo_actualizado = await pb.get_record("vuelos_catalogo", vuelo["id"])
    assert vuelo_actualizado["precio_base"] == 134.0

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="vuelo" && estado="exitoso"')
    if log:
        await pb.delete_record("sincronizaciones_log", log["id"])
    await pb.delete_record("tarifas_vuelo", tarifa_business["id"])
    await pb.delete_record("tarifas_vuelo", tarifa_first["id"])


async def test_enriquecer_con_google_flights_sin_resultado_no_actualiza(pb, vuelo_factory, google_flights_falso):
    await vuelo_factory(origen_codigo="ATL", destino_codigo="JFK", fecha_salida=FECHA_TEST_ISO)

    cliente = google_flights_falso(resultados_por_ruta={})  # ninguna ruta configurada -> siempre None

    resumen = await enriquecer_con_google_flights(cliente, hoy=FECHA_TEST, rutas=[("ATL", "JFK")])
    assert resumen["actualizados"] == 0

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="vuelo" && estado="parcial"')
    if log:
        await pb.delete_record("sincronizaciones_log", log["id"])


# ── RF-VUE-T06 (CU-T41, rotación de clases de cabina) ─────────────────────

async def test_enriquecer_con_google_flights_respeta_clases_explicitas(
    pb, vuelo_factory, tarifa_factory, google_flights_falso
):
    """Pasar `clases=("economy",)` (equivalente a lo que arma `_clases_activas`
    cuando el admin apagó business/first en CU-T41) hace UNA sola llamada por
    ruta en vez de 3 — la defensa real contra gastar cuota de más."""
    vuelo = await vuelo_factory(
        origen_codigo="ATL", destino_codigo="JFK", fecha_salida=FECHA_TEST_ISO,
        numero_vuelo="DL466", precio_base=100.0,
    )
    tarifa = await tarifa_factory(vuelo["id"], precio_final=100.0)
    await pb.update_record("tarifas_vuelo", tarifa["id"], {"clase_cabina": "economy"})

    cliente = google_flights_falso(
        resultados_por_ruta={
            ("ATL", "JFK"): {
                "vuelos": [{"numero_vuelo": "DL466", "precio": 134.0, "emisiones_co2_kg": None,
                            "fuente_busqueda_ref": None, "detalles_extra": None}],
                "predicciones": None,
            }
        }
    )

    resumen = await enriquecer_con_google_flights(
        cliente, hoy=FECHA_TEST, rutas=[("ATL", "JFK")], clases=("economy",)
    )
    assert resumen["procesados"] == 1  # una sola clase -> una sola llamada, no 3
    assert resumen["actualizados"] == 1
    assert len(cliente.llamadas) == 1
    assert cliente.llamadas[0].endswith(":economy")

    # sin business/first en `clases`, no se crea ninguna tarifa premium nueva
    premium = await pb.get_first(
        "tarifas_vuelo", f'vuelo_id="{vuelo["id"]}" && (clase_cabina="business" || clase_cabina="first")'
    )
    assert premium is None

    log = await pb.get_first("sincronizaciones_log", 'tipo_producto="vuelo" && estado="exitoso"')
    if log:
        await pb.delete_record("sincronizaciones_log", log["id"])


async def test_clases_activas_lee_config_y_respeta_orden(pb):
    from app.vuelos.services.enriquecimiento_service import _clases_activas

    repo = VuelosRepository()
    registro = await pb.get_first("configuracion_sistema", 'clave="vuelos.google_flights_clases_activas"')
    assert registro is not None, "scripts/pb_schema_asientos_v31.py o el seed manual de CU-T41 debe correr antes"
    valor_original = registro["valor"]

    try:
        await pb.update_record("configuracion_sistema", registro["id"], {"valor": "first,economy"})
        activas = await _clases_activas(repo)
        # el orden de salida sigue CLASES_CABINA (economy antes que first),
        # no el orden en que el admin tipeó el valor guardado
        assert activas == ("economy", "first")

        # `valor` es text requerido en PocketBase — no se puede guardar vacío
        # desde la UI (el router también lo bloquea, ver config_rotacion_cabina_submit);
        # el fallback a default de `_clases_activas` cubre en cambio la clave
        # ausente del todo (entorno recién migrado, antes del primer seed).
        await pb.delete_record("configuracion_sistema", registro["id"])
        activas_sin_clave = await _clases_activas(repo)
        assert set(activas_sin_clave) == {"economy", "business", "first"}
    finally:
        existe = await pb.get_first("configuracion_sistema", 'clave="vuelos.google_flights_clases_activas"')
        if existe:
            await pb.update_record("configuracion_sistema", existe["id"], {"valor": valor_original})
        else:
            admin = await pb.get_first("usuarios", 'email="btoaquizaz@uteq.edu.ec"')
            await pb.create_record(
                "configuracion_sistema",
                {
                    "clave": "vuelos.google_flights_clases_activas",
                    "valor": valor_original,
                    "categoria": "vuelos",
                    "descripcion": "RF-VUE-T06 (CU-T41) — qué clases de cabina participan de la rotación diaria de Google Flights (coma-separado).",
                    "modificado_por": admin["id"],
                },
            )
