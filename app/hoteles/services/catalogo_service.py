"""RF-HOT-004,005 (CU-O118) — genera `hoteles_catalogo`/`hoteles_tarifas`
y cachea `hoteles_resenas`, orquestando el flujo real de 3 pasos de
HotelLens (ver `hotellens_client.py`) + reseñas. Cada corrida se registra
en `sincronizaciones_log` (RNF: módulo Integraciones es dueño de esa
colección, este servicio solo escribe).

RNF-HOT-002: esta función solo escribe en las 3 tablas propias del módulo
— nunca toca `proveedores_comerciales` más allá de leerlo (no aplica aquí,
no se resuelve comisión en esta fase).
"""

import datetime

from app.hoteles.repositories.hoteles_repo import HotelesRepository
from app.hoteles.services.hotellens_client import HotelLensClient, extraer_hotel_id_booking
from app.shared.cuota_service import hay_cupo
from app.shared.rotacion_ciudades import rebanada_rotativa

CIUDADES_DEFAULT = ["Paris", "Madrid", "New York"]
MAX_HOTELES_POR_CIUDAD_DEFAULT = 2
CIUDADES_POR_CORRIDA_DEFAULT = 3
DIAS_ADELANTE_DEFAULT = 60
CUPOS_DEFAULT = 10


def _ahora_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z")


def _num(valor, default=None):
    try:
        return float(valor) if valor is not None else default
    except (TypeError, ValueError):
        return default


async def _generar_disponibilidad_sintetica_hotel(
    repo: HotelesRepository, hotel_id: str, hotel_tarifa_id: str, cupos_seed: float | None
) -> int:
    """RF-HOT-004 (gap real cerrado 2026-07-29, ver errores-conocidos.md) —
    antes check-in/check-out eran cosméticos: ninguna fila tenía cupo por
    noche. Mismo patrón que `actividades_horarios`
    (`_generar_disponibilidad_sintetica` en el módulo Actividades): ventana
    móvil que se regenera completa en cada refresh de catálogo, no se
    acumula sobre lo ya generado (la fila padre `hoteles_tarifas` también se
    borra y recrea entera en cada corrida, ver `eliminar_tarifas_de_hotel`)."""
    dias_valor = await repo.config("disponibilidad_hoteles.dias_adelante")
    dias_adelante = int(dias_valor) if dias_valor else DIAS_ADELANTE_DEFAULT
    cupos_default_valor = await repo.config("disponibilidad_hoteles.cupos_default")
    cupos_default = int(cupos_default_valor) if cupos_default_valor else CUPOS_DEFAULT
    # Preferir la señal real de HotelLens (`rooms_left`, ya en
    # `hoteles_tarifas.cupos_disponibles`) sobre el fallback sintético —
    # es el único dato de inventario real que esta fuente sí entrega.
    cupos = int(cupos_seed) if cupos_seed is not None else cupos_default

    hoy = datetime.date.today()
    ahora = _ahora_iso()
    creados = 0
    for dia_offset in range(dias_adelante):
        fecha = hoy + datetime.timedelta(days=dia_offset)
        await repo.crear_disponibilidad(
            {
                "hotel_id": hotel_id,
                "hotel_tarifa_id": hotel_tarifa_id,
                "fecha": fecha.isoformat(),
                "cupos_disponibles": cupos,
                "fecha_actualizacion": ahora,
            }
        )
        creados += 1
    return creados


async def _procesar_hotel(repo: HotelesRepository, client: HotelLensClient, item_busqueda: dict, check_in: str, check_out: str) -> bool:
    """Un hotel encontrado en la búsqueda (paso 1) -> intenta resolverlo a
    detalle real de Booking.com (pasos 2-3) + reseñas. Devuelve True si se
    creó/actualizó con datos reales de tarifas, False si no se pudo resolver
    un hotel_id de Booking.com (oferta no disponible para ese resultado —
    no es un error, algunos resultados de Google Hotels no tienen match en
    Booking.com)."""
    nombre = item_busqueda.get("name")
    url_entidad = item_busqueda.get("url")
    if not nombre or not url_entidad:
        return False

    ofertas = await client.obtener_ofertas(url_entidad)
    hotel_id_booking = None
    for oferta in ofertas:
        booking_url = oferta.get("booking_url") or ""
        hotel_id_booking = extraer_hotel_id_booking(booking_url)
        if hotel_id_booking:
            break
    if not hotel_id_booking:
        return False

    detalle = await client.obtener_detalle_booking(hotel_id_booking, check_in, check_out)
    room_offers = detalle.get("room_offers") or []
    if not room_offers:
        return False

    ahora = _ahora_iso()
    pais_codigo = detalle.get("country_code") or ""
    hotel_data = {
        "nombre": nombre,
        "direccion": detalle.get("address") or "",
        "ciudad": detalle.get("city") or item_busqueda.get("city") or "",
        "pais": pais_codigo.upper() if pais_codigo else (detalle.get("country") or ""),
        "latitud": _num(detalle.get("latitude")),
        "longitud": _num(detalle.get("longitude")),
        "estrellas": _num(item_busqueda.get("stars")),
        "calificacion_promedio": _num(item_busqueda.get("rating")),
        "cantidad_resenas": _num(item_busqueda.get("reviews")),
        # category_scores confirmado ausente en /booking/hotels/details (solo
        # lo trae el /details nativo de Google Hotels, no usado en este flujo
        # de 3 pasos) — queda vacío, no es un dato que este endpoint tenga.
        "category_scores": detalle.get("category_scores") or {},
        "descripcion_corta": "",
        "descripcion": detalle.get("description") or "",
        "servicios": detalle.get("amenities") or [],
        # Confirmado en vivo 2026-07-19: la respuesta real usa
        # `checkin_from`/`checkout_until`, no `check_in_time`/`check_out_time`.
        "hora_checkin": detalle.get("checkin_from") or "",
        "hora_checkout": detalle.get("checkout_until") or "",
        "imagen_principal": item_busqueda.get("image_url") or "",
        "fuente_entity_url": url_entidad,
        "fecha_actualizacion": ahora,
    }

    existente = await repo.hotel_por_fuente_entity_url(url_entidad)
    if existente:
        hotel = await repo.actualizar_hotel(existente["id"], hotel_data)
    else:
        hotel = await repo.crear_hotel(hotel_data)

    # Tarifas: snapshot point-in-time del proveedor (RN-HOT-001) — se
    # reemplazan completas en cada corrida, no se acumulan versiones viejas.
    await repo.eliminar_tarifas_de_hotel(hotel["id"])
    for oferta_habitacion in room_offers:
        cupos_seed = _num(oferta_habitacion.get("rooms_left"))
        tarifa = await repo.crear_tarifa(
            {
                "hotel_id": hotel["id"],
                "tipo_habitacion": oferta_habitacion.get("room_name") or "Habitación estándar",
                "bed_type": oferta_habitacion.get("bed_type"),
                "max_ocupantes": _num(oferta_habitacion.get("max_occupancy")),
                "tamano_m2": _num(oferta_habitacion.get("room_size_m2")),
                "desayuno_incluido": bool(oferta_habitacion.get("breakfast_included")),
                # Confirmado en vivo 2026-07-19: las claves reales son
                # `total_price`/`nightly_price` (no `price`) — pueden venir
                # null en ofertas "pay at property"/sin prepago, 0.0 como
                # último recurso (mismo criterio que tarifas_vuelo sintético).
                "precio_final": _num(
                    oferta_habitacion.get("total_price") or oferta_habitacion.get("nightly_price"), 0.0
                ),
                "moneda": oferta_habitacion.get("currency") or "USD",
                "reembolsable": bool(oferta_habitacion.get("free_cancellation")),
                # `refundable_until` real viene "" (no null) cuando no aplica
                # — PocketBase rechaza "" en un campo date, se normaliza a None.
                "cancelacion_hasta": oferta_habitacion.get("refundable_until") or None,
                # RN-HOT-004: HotelLens no expone si una tarifa admite pago
                # diferido (no es un dato real de la fuente) — se deriva de
                # `reembolsable` como criterio de riesgo sintético, documentado
                # (mismo patrón que otros defaults sintéticos de este módulo,
                # ver `scripts/pb_schema_pago_diferido_hotel.py`).
                "pago_diferido_disponible": bool(oferta_habitacion.get("free_cancellation")),
                "cupos_disponibles": cupos_seed,
                "fecha_actualizacion": ahora,
            }
        )
        # Disponibilidad real por noche (RF-HOT-004, gap cerrado 2026-07-29)
        # — sin esto la tarifa no es reservable con fecha real.
        await _generar_disponibilidad_sintetica_hotel(repo, hotel["id"], tarifa["id"], cupos_seed)

    # Reseñas (RF-HOT-005) — se cachean junto con el catálogo para no gastar
    # cuota consultando /reviews en cada vista de detalle.
    resenas = await client.obtener_resenas(url_entidad)
    await repo.eliminar_resenas_de_hotel(hotel["id"])
    for resena in resenas:
        await repo.crear_resena(
            {
                "hotel_id": hotel["id"],
                "autor": resena.get("author"),
                "calificacion": _num(resena.get("rating")),
                "escala_calificacion": _num(resena.get("rating_scale"), 5.0),
                "comentario": resena.get("text"),
                "fecha_relativa_texto": resena.get("relative_date"),
                "fuente": resena.get("source"),
                "fecha_actualizacion": ahora,
            }
        )

    return True


async def generar_catalogo(
    client: HotelLensClient,
    ciudades: list[str] | None = None,
    max_hoteles_por_ciudad: int | None = None,
    check_in: str | None = None,
    check_out: str | None = None,
) -> dict:
    repo = HotelesRepository()

    if ciudades is None:
        valor = await repo.config("hoteles.ciudades_seed")
        universo = [c.strip() for c in valor.split(",")] if valor else CIUDADES_DEFAULT
        valor_corrida = await repo.config("hoteles.ciudades_por_corrida")
        ciudades_por_corrida = int(valor_corrida) if valor_corrida else CIUDADES_POR_CORRIDA_DEFAULT
        # RF-HOT-004 — rotación determinística por día-del-año: cada corrida
        # solo toca `ciudades_por_corrida` del universo curado, para no
        # exceder el rate limit por minuto de HotelLens en una sola corrida
        # (ver app/shared/rotacion_ciudades.py).
        ciudades = rebanada_rotativa(universo, ciudades_por_corrida)
    if max_hoteles_por_ciudad is None:
        valor = await repo.config("hoteles.max_hoteles_por_ciudad")
        max_hoteles_por_ciudad = int(valor) if valor else MAX_HOTELES_POR_CIUDAD_DEFAULT

    hoy = datetime.date.today()
    check_in = check_in or (hoy + datetime.timedelta(days=30)).isoformat()
    check_out = check_out or (hoy + datetime.timedelta(days=31)).isoformat()

    fuente = await repo.fuente_por_nombre("HotelLens")
    fecha_inicio = _ahora_iso()
    procesados = resueltos = 0
    error_detalle = None
    motivo_parcial = None

    try:
        for ciudad in ciudades:
            # RF-HOT-004 — gate real de cuota mensual (límite duro 100/mes,
            # plan Basic RapidAPI): corta ANTES de empezar una ciudad nueva
            # si ya no hay margen. La rotación de ciudades solo da variedad,
            # esto es lo que de verdad protege el techo (ver
            # app/shared/cuota_service.py).
            if fuente and not await hay_cupo(
                fuente["id"], fuente.get("cuota_mensual_estimada"), getattr(client, "llamadas_realizadas", 0)
            ):
                motivo_parcial = "cuota_mensual_agotada"
                break
            resultados = await client.buscar_hoteles(ciudad)
            for item in resultados[:max_hoteles_por_ciudad]:
                procesados += 1
                if await _procesar_hotel(repo, client, item, check_in, check_out):
                    resueltos += 1
        estado = "exitoso" if resueltos > 0 else "parcial"
    except Exception as exc:  # noqa: BLE001 — se registra en la bitácora, no se oculta
        estado = "fallido"
        error_detalle = str(exc)

    if fuente:
        await repo.crear_log_sincronizacion(
            {
                "fuente_id": fuente["id"],
                "tipo_producto": "hotel",
                "fecha_inicio": fecha_inicio,
                "fecha_fin": _ahora_iso(),
                "estado": estado,
                "registros_procesados": procesados,
                "registros_nuevos": resueltos,
                "registros_actualizados": 0,
                "unidades_cuota_consumidas": getattr(client, "llamadas_realizadas", 0),
                "error_detalle": error_detalle,
            }
        )

    resumen = {"ciudades": ciudades, "procesados": procesados, "resueltos": resueltos, "estado": estado}
    if error_detalle:
        resumen["error_detalle"] = error_detalle
    if motivo_parcial:
        resumen["motivo_parcial"] = motivo_parcial
    print(f"[HOTELES] {resumen}")
    return resumen
