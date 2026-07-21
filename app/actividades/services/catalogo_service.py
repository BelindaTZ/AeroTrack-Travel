"""RF-ACT-004,005 (CU-O120) — genera `actividades_catalogo`/
`actividades_resenas` desde Travel Advisor. RF-ACT-006 (CU-O121) — genera
`actividades_horarios` por regla de negocio en el mismo ciclo, ya que sin
disponibilidad ninguna actividad del catálogo es reservable (CU-O68).

RN-ACT-001: `inclusiones`/`punto_encuentro`/`condiciones` son curación
manual — esta función nunca los escribe.
RN-ACT-002: el origen sintético de `actividades_horarios` no se oculta ni
se disfraza de cupo real (mismo criterio que `tarifas_vuelo.cupos_disponibles`).
RNF-ACT-001: solo se escribe en `actividades_catalogo`/`actividades_resenas`/
`actividades_horarios` (más `sincronizaciones_log`, de Integraciones).
"""

import datetime

from app.actividades.repositories.actividades_repo import ActividadesRepository
from app.actividades.services.traveladvisor_client import TravelAdvisorClient, parsear_tracking_key
from app.shared.cuota_service import hay_cupo
from app.shared.rotacion_ciudades import rebanada_rotativa

CIUDADES_DEFAULT = ["Paris", "Madrid", "New York"]
MAX_ACTIVIDADES_POR_CIUDAD_DEFAULT = 3
CIUDADES_POR_CORRIDA_DEFAULT = 4

CUPOS_DEFAULT = 15
HORARIOS_POR_DIA_DEFAULT = ["09:00", "13:00", "16:00"]
DIAS_ADELANTE_DEFAULT = 14


def _ahora_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z")


def _num(valor, default=None):
    try:
        return float(valor) if valor is not None else default
    except (TypeError, ValueError):
        return default


async def _generar_disponibilidad_sintetica(repo: ActividadesRepository, actividad_id: str, precio: float) -> int:
    """RF-ACT-006/CU-O121 — ventana móvil, mismo patrón que
    `catalogo_vuelos_tasks.generar_vuelos_programables` (Vuelos): cada
    corrida reemplaza los horarios futuros y regenera la ventana completa,
    no acumula sobre lo ya generado."""
    cupos_valor = await repo.config("disponibilidad_actividades.cupos_default")
    cupos = int(cupos_valor) if cupos_valor else CUPOS_DEFAULT
    horarios_valor = await repo.config("disponibilidad_actividades.horarios_por_dia")
    horarios = [h.strip() for h in horarios_valor.split(",")] if horarios_valor else HORARIOS_POR_DIA_DEFAULT
    dias_valor = await repo.config("disponibilidad_actividades.dias_adelante")
    dias_adelante = int(dias_valor) if dias_valor else DIAS_ADELANTE_DEFAULT

    hoy = datetime.date.today()
    await repo.eliminar_horarios_futuros_de_actividad(actividad_id, hoy.isoformat())

    ahora = _ahora_iso()
    creados = 0
    for dia_offset in range(dias_adelante):
        fecha = hoy + datetime.timedelta(days=dia_offset)
        for hora in horarios:
            await repo.crear_horario(
                {
                    "actividad_id": actividad_id,
                    "fecha": fecha.isoformat(),
                    "hora": hora,
                    "cupos_disponibles": cupos,
                    "precio": precio,
                    "moneda": "USD",
                    "fecha_actualizacion": ahora,
                }
            )
            creados += 1
    return creados


async def _procesar_actividad(repo: ActividadesRepository, client: TravelAdvisorClient, card: dict, ciudad: str) -> bool:
    tracking = parsear_tracking_key(card.get("trackingKey"))
    content_id = tracking.get("lid")
    if content_id is None:
        return False
    content_id = str(content_id)

    detalle = await client.obtener_detalle(content_id)
    if not detalle.get("name"):
        return False

    ahora = _ahora_iso()
    address_obj = detalle.get("address_obj") or {}
    actividad_data = {
        "nombre": detalle["name"],
        "ciudad": address_obj.get("city") or ciudad,
        "pais": address_obj.get("country") or "",
        "categoria": (card.get("primaryInfo") or {}).get("text") or (detalle.get("category") or {}).get("name") or "",
        "calificacion_promedio": _num(detalle.get("rating")) or _num(tracking.get("br")),
        "cantidad_resenas": _num(detalle.get("num_reviews")) or _num(tracking.get("rc")),
        "descripcion": detalle.get("description") or "",
        "precio_desde": _num(tracking.get("prc")),
        "moneda": tracking.get("cur") or "USD",
        "imagen_principal": ((card.get("cardPhoto") or {}).get("sizes") or {}).get("urlTemplate") or "",
        "fuente_content_id": content_id,
        "fecha_actualizacion": ahora,
    }

    existente = await repo.actividad_por_content_id(content_id)
    if existente:
        actividad = await repo.actualizar_actividad(existente["id"], actividad_data)
    else:
        actividad = await repo.crear_actividad(actividad_data)

    # Reseñas (RF-ACT-005) — ya vienen embebidas en el mismo get-details.
    resenas = detalle.get("reviews") or []
    await repo.eliminar_resenas_de_actividad(actividad["id"])
    for resena in resenas:
        await repo.crear_resena(
            {
                "actividad_id": actividad["id"],
                "autor": resena.get("author"),
                "calificacion": _num(resena.get("rating")),
                "comentario": resena.get("summary"),
                "fecha_resena": resena.get("published_date"),
                "fecha_actualizacion": ahora,
            }
        )

    # Disponibilidad sintética (RF-ACT-006) — sin esto la actividad no es
    # reservable (CU-O68/O69), se genera en el mismo ciclo del catálogo.
    precio_base = actividad_data["precio_desde"] or 0.0
    await _generar_disponibilidad_sintetica(repo, actividad["id"], precio_base)

    return True


async def generar_catalogo(
    client: TravelAdvisorClient, ciudades: list[str] | None = None, max_actividades_por_ciudad: int | None = None
) -> dict:
    repo = ActividadesRepository()

    if ciudades is None:
        valor = await repo.config("actividades.ciudades_seed")
        universo = [c.strip() for c in valor.split(",")] if valor else CIUDADES_DEFAULT
        valor_corrida = await repo.config("actividades.ciudades_por_corrida")
        ciudades_por_corrida = int(valor_corrida) if valor_corrida else CIUDADES_POR_CORRIDA_DEFAULT
        # RF-ACT-004 — rotación determinística por día-del-año: da variedad
        # de ciudades entre corridas. La protección real contra el límite
        # duro real de Travel Advisor (500 req/mes, plan Basic RapidAPI) es
        # el gate de app/shared/cuota_service.py más abajo.
        ciudades = rebanada_rotativa(universo, ciudades_por_corrida)
    if max_actividades_por_ciudad is None:
        valor = await repo.config("actividades.max_actividades_por_ciudad")
        max_actividades_por_ciudad = int(valor) if valor else MAX_ACTIVIDADES_POR_CIUDAD_DEFAULT

    fuente = await repo.fuente_por_nombre("Travel Advisor")
    fecha_inicio = _ahora_iso()
    procesados = resueltos = 0
    error_detalle = None
    motivo_parcial = None

    try:
        for ciudad in ciudades:
            if fuente and not await hay_cupo(
                fuente["id"], fuente.get("cuota_mensual_estimada"), getattr(client, "llamadas_realizadas", 0)
            ):
                motivo_parcial = "cuota_mensual_agotada"
                break
            geo_id = await client.resolver_geo_id(ciudad)
            if geo_id is None:
                continue

            tarjetas = await client.buscar_actividades(geo_id)
            for card in tarjetas[:max_actividades_por_ciudad]:
                procesados += 1
                if await _procesar_actividad(repo, client, card, ciudad):
                    resueltos += 1
        estado = "exitoso" if resueltos > 0 else "parcial"
    except Exception as exc:  # noqa: BLE001 — se registra en la bitácora, no se oculta
        estado = "fallido"
        error_detalle = str(exc)

    if fuente:
        await repo.crear_log_sincronizacion(
            {
                "fuente_id": fuente["id"],
                "tipo_producto": "actividad",
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
    if motivo_parcial:
        resumen["motivo_parcial"] = motivo_parcial
    if error_detalle:
        resumen["error_detalle"] = error_detalle
    print(f"[ACTIVIDADES] {resumen}")
    return resumen
