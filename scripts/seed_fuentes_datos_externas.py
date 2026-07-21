"""Siembra idempotente (upsert por `nombre`) de `fuentes_datos_externas`
(CU-T37) — las ~18 fuentes reales conocidas del sistema, según
`specs/tactico/integraciones/tasks.md` T006: 15 filas `constante` /
`catalogo_periodico` / `cache_bajo_demanda` con host real (probadas vía
curl en sesiones anteriores, documentadas en `docs/apis-reference.md`) +
4 filas `regla_negocio_interna` (disponibilidad sintética, sin host real,
ya vigentes en código — `tarifas_vuelo.cupos_disponibles`, etc.).

`host_env_var` es solo el NOMBRE de la variable de entorno, nunca el valor
(REG-B3) — dos ya confirmados reales en `docs/apis-reference.md`/
`docs/apis-listas-implementacion.md`: `SENDGRID_KEY`, `FLIGHT_STATUS_API_KEY`
(AviationStack). El resto sigue el mismo patrón `_API_HOST` que ya
documentaba el propio dbml v3 como ejemplo (`HOTELLENS_API_HOST`) para los
proveedores vía RapidAPI.

`frecuencia_sincronizacion_horas` solo se puebla en `catalogo_periodico`
(según el propio esquema) — el resto queda null.

`cuota_mensual_estimada` (agregado por
`scripts/pb_schema_integraciones_fix_cuota.py`) documenta el techo mensual
real de cada fuente, confirmado en el panel de RapidAPI (no solo por
ausencia de 429 en pruebas, que había llevado a subestimarlo): HotelLens
100/mes, Global Rental Cars 100/mes, Travel Advisor 500/mes, Cruise Pricing
~500k/mes. Este campo SÍ gatea: `app/shared/cuota_service.py` lo usa antes
de procesar cada ciudad nueva en `catalogo_service.generar_catalogo()`
(hoteles/autos/actividades), sumando lo ya consumido en
`sincronizaciones_log.unidades_cuota_consumidas` del mes en curso.

Re-ejecutable: si la fuente ya existe pero `cuota_mensual_estimada`/`notas`
cambiaron en este script, se actualiza (no solo se crea la primera vez).

Ejecutar: python scripts/seed_fuentes_datos_externas.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

# (nombre, tipo_uso, host_env_var, tipo_producto_alimentado, frecuencia_horas, notas, cuota_mensual_estimada)
FUENTES = [
    ("AeroDataBox", "catalogo_periodico", "AERODATABOX_API_HOST", "vuelo", 24,
     "FIDS + risk score (delayIndex). Cuota 600/mes, statistical API cara (~6 unidades/llamada).", 600),
    ("Google Flights (SerpApi)", "catalogo_periodico", "SERPAPI_API_KEY", "vuelo", 24,
     "Único proveedor con precio real + price_insights (predicción) + clase de cabina real. Cuota 250/mes.", 250),
    ("HotelLens", "catalogo_periodico", "HOTELLENS_API_HOST", "hotel", 12,
     "Catálogo elegido para Hoteles (Google Hotels). Plan Basic RapidAPI confirmado: 100 req/mes (límite "
     "duro) + 10 req/min. El gate real es app/shared/cuota_service.py; el throttle de 13s entre llamadas "
     "en hotellens_client.py cubre el límite por minuto.", 100),
    ("Global Rental Cars", "catalogo_periodico", "GLOBALRENTALCARS_API_HOST", "auto", 24,
     "Priceline/Booking/Expedia agregados. Precios point-in-time, revalidar antes de confirmar. Plan Basic "
     "RapidAPI confirmado: 100 req/mes (límite duro) + 1000 req/hora — gateado por app/shared/cuota_service.py.", 100),
    ("Travel Advisor", "catalogo_periodico", "TRAVELADVISOR_API_HOST", "actividad", 24,
     "Catálogo elegido para Actividades. Sin disponibilidad real (ver reglas_negocio_interna abajo). Plan "
     "Basic RapidAPI confirmado: 500 req/mes (límite duro) + 5 req/seg — gateado por app/shared/cuota_service.py.", 500),
    ("Cruise Pricing API", "catalogo_periodico", "CRUISEPRICING_API_HOST", "crucero", 24,
     "10/11 endpoints funcionales (falta /price-history, requiere plan PRO). Sin disponibilidad real. "
     "CORREGIDO 2026-07-20: plan Basic RapidAPI confirmado 100 req/mes (límite duro) + 10 req/min — el "
     "supuesto previo de ~500k/mes venía de headers de rate-limit por ventana mal interpretados como techo "
     "mensual real. Gateado por app/shared/cuota_service.py igual que los otros 3.", 100),
    ("ExchangeRate-API", "cache_bajo_demanda", "EXCHANGERATE_API_HOST", None, None,
     "Alimenta tasas_cambio (RF-FAC-011). Se cachea al primer uso del día, no es sync periódico clásico.", None),
    ("Visa Requirement", "cache_bajo_demanda", "VISAREQUIREMENT_API_HOST", None, None,
     "Alimenta requisitos_visa_cache (CU-O81). Universo pasaporte×destino demasiado grande para pre-computar.", None),
    ("SendGrid", "constante", "SENDGRID_KEY", None, None, "API nativa (no wrapper RapidAPI). Envío de campañas/notificaciones.", None),
    ("Gmail API", "constante", "GMAIL_API_CLIENT_SECRET", None, None, "Monitoreo de correo (CU-O29) y escalación (CU-O100/T36).", None),
    ("OpenSky Network", "constante", "OPENSKY_API_HOST", None, None, "Posición en tiempo real (RF-DIS-008), proxy en vivo sin tabla propia.", None),
    ("Stripe", "constante", "STRIPE_SECRET_KEY", None, None, "Pagos, authorize+capture para pago diferido (RF-FAC-012).", None),
    ("Groq", "constante", "GROQ_API_KEY", None, None, "Asistente IA — modelo primario o de respaldo, según config.", None),
    ("Gemini", "constante", "GEMINI_API_KEY", None, None, "Asistente IA — modelo primario o de respaldo, según config.", None),
    ("AviationStack", "constante", "FLIGHT_STATUS_API_KEY", None, None,
     "YA EN PRODUCCIÓN — CU-O40, dag_estado_real_vuelo.py. Cuota 100/mes, límite operativo 90.", 100),
    ("Google Places API", "constante", "GOOGLE_CLOUD_PLACES_API_KEY", None, None,
     "app/shared/google_apis/places_client.py. Sin UI conectada (2026-07-20) — base para el selector "
     "estilo Despegar. Límite real: 100/día autocomplete+getPlace (no mensual, gateado por "
     "app/shared/cuota_service.cupo_diario_disponible). Cuota de Google Cloud, normalmente ajustable "
     "desde la consola una vez verificada la facturación — a diferencia del plan fijo de RapidAPI.", None),
    ("Google Geocoding API", "constante", "GOOGLE_CLOUD_GEOCODING_API_KEY", None, None,
     "app/shared/google_apis/geocoding_client.py, endpoint CLÁSICO (/maps/api/geocode/json) a propósito: "
     "sin límite diario configurado (la variante 'New'/v4 sí tiene 100/día). Sin gate, sin UI conectada.", None),
    ("Google Maps Embed API", "constante", "GOOGLE_CLOUD_MAPS_EMBED_API_KEY", None, None,
     "app/shared/google_apis/maps_embed.py — NO es un cliente HTTP, el navegador del usuario carga el "
     "iframe directo, nuestro backend nunca llama a Google aquí. Conectada en detalle de hotel (CU-O55, "
     "ubicación) y crucero (CU-O72, ruta). Sin cuota configurada en el sistema.", None),
    ("Google Maps JavaScript API", "constante", "GOOGLE_CLOUD_MAPS_JAVASCRIPT_API_KEY", None, None,
     "Sin cliente ni UI conectada todavía — necesita el primer JS propio del proyecto (hoy 100% Jinja2 "
     "server-rendered). Key ya sembrada, lista para la fase del dropdown/mapa interactivo. Límite real: "
     "map loads sin límite diario (30,000/min); Maps Grounding Widget 1,000/día.", None),
    ("Google Routes API", "constante", "GOOGLE_CLOUD_ROUTES_API_KEY", None, None,
     "app/shared/google_apis/routes_client.py (ComputeRoutes). Sin UI conectada — candidata a mostrar "
     "'distancia al centro' en tarjetas de hotel (visto en el análisis de Despegar). Límite real: 100/día "
     "(no mensual, gateado por app/shared/cuota_service.cupo_diario_disponible).", None),
    ("Disponibilidad tarifas_vuelo (regla fija)", "regla_negocio_interna", None, "vuelo", None,
     "Sin fuente real confirmada (ninguna API da cupos de vuelo) — valores fijos Light=120/Standard=80/Flex=30.", None),
    ("Disponibilidad Asientos (regla fija)", "regla_negocio_interna", None, "vuelo", None,
     "Mapa de asientos generado por reglas de negocio (es_premium/recargo), no por proveedor externo.", None),
    ("Disponibilidad Actividades (regla fija)", "regla_negocio_interna", None, "actividad", None,
     "Confirmado sin fuente real — ni Travel Advisor expone disponibilidad por fecha/hora.", None),
    ("Disponibilidad Cruceros (regla fija)", "regla_negocio_interna", None, "crucero", None,
     "Confirmado sin fuente real — Cruise Pricing API no expone inventario de camarotes.", None),
]


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def main() -> None:
    headers = {"Authorization": admin_token()}

    admins = httpx.get(
        f"{PB_URL}/api/collections/usuarios/records",
        params={"filter": 'tipo_actor="administrador"', "perPage": 1},
        headers=headers,
        timeout=10,
    ).json()["items"]
    if not admins:
        raise RuntimeError("No hay ningún usuario administrador sembrado")
    admin_id = admins[0]["id"]

    existentes = httpx.get(
        f"{PB_URL}/api/collections/fuentes_datos_externas/records", params={"perPage": 200}, headers=headers, timeout=10
    ).json()["items"]
    existentes_por_nombre = {f["nombre"]: f for f in existentes}

    for nombre, tipo_uso, host_env_var, tipo_producto, frecuencia, notas, cuota_mensual_estimada in FUENTES:
        payload = {
            "nombre": nombre,
            "tipo_uso": tipo_uso,
            "activa": True,
            "notas": notas,
            "modificado_por": admin_id,
            "cuota_mensual_estimada": cuota_mensual_estimada,
        }
        if host_env_var:
            payload["host_env_var"] = host_env_var
        if tipo_producto:
            payload["tipo_producto_alimentado"] = tipo_producto
        if frecuencia:
            payload["frecuencia_sincronizacion_horas"] = frecuencia

        actual = existentes_por_nombre.get(nombre)
        if actual:
            if actual.get("notas") == notas and actual.get("cuota_mensual_estimada") == cuota_mensual_estimada:
                print(f"= {nombre} ya existe")
                continue
            resp = httpx.patch(
                f"{PB_URL}/api/collections/fuentes_datos_externas/records/{actual['id']}",
                json={"notas": notas, "cuota_mensual_estimada": cuota_mensual_estimada, "modificado_por": admin_id},
                headers=headers,
                timeout=10,
            )
            if resp.status_code >= 400:
                print(f"! error actualizando {nombre}: {resp.status_code} {resp.text}")
                continue
            print(f"~ {nombre} actualizado (cuota_mensual_estimada={cuota_mensual_estimada})")
            continue

        resp = httpx.post(
            f"{PB_URL}/api/collections/fuentes_datos_externas/records", json=payload, headers=headers, timeout=10
        )
        if resp.status_code >= 400:
            print(f"! error creando {nombre}: {resp.status_code} {resp.text}")
            continue
        print(f"+ {nombre} ({tipo_uso})")

    print("Listo.")


if __name__ == "__main__":
    main()
