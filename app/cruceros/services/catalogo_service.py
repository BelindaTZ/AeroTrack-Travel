"""RF-CRU-005 (CU-O122) — genera `navieras`/`barcos`/`cruceros_catalogo`/
`cruceros_camarotes_tarifa` desde Cruise Pricing API. RF-CRU-006 (CU-O123)
— genera `cupos_disponibles` sintético en el mismo ciclo (sin esto ningún
camarote sería seleccionable, CU-O75), mismo criterio que Actividades:
sin fuente real de inventario confirmada, no se separa en un servicio aparte.

RNF: solo se escribe en las 4 tablas propias del módulo (más
`sincronizaciones_log`, de Integraciones).
"""

import datetime

from app.cruceros.repositories.cruceros_repo import CrucerosRepository
from app.cruceros.services.cruisepricing_client import CruisePricingClient
from app.shared.cuota_service import hay_cupo

LIMITE_CRUCEROS_DEFAULT = 10
CUPOS_DEFAULT = 20


def _ahora_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z")


def _num(valor, default=None):
    try:
        return float(valor) if valor is not None else default
    except (TypeError, ValueError):
        return default


async def _asegurar_naviera(repo: CrucerosRepository, slug: str, navieras_reales: dict[str, dict], ahora: str) -> dict:
    existente = await repo.naviera_por_slug(slug)
    info_real = navieras_reales.get(slug, {})
    data = {
        "nombre": info_real.get("display_name") or slug,
        "slug_proveedor": slug,
        "destinos": info_real.get("destinations") or [],
        "fecha_actualizacion": ahora,
    }
    if existente:
        return await repo.actualizar_naviera(existente["id"], data)
    return await repo.crear_naviera(data)


async def _asegurar_barco(repo: CrucerosRepository, naviera_id: str, nombre: str, ahora: str) -> dict:
    existente = await repo.barco_por_naviera_y_nombre(naviera_id, nombre)
    if existente:
        return existente
    return await repo.crear_barco({"naviera_id": naviera_id, "nombre": nombre, "fecha_actualizacion": ahora})


async def _generar_camarotes(repo: CrucerosRepository, crucero_id: str, cupos_default: int, precios_camarote: dict) -> int:
    ahora = _ahora_iso()
    await repo.eliminar_camarotes_de_crucero(crucero_id)
    creados = 0
    for tipo_camarote, precio in precios_camarote.items():
        precio_num = _num(precio)
        if precio_num is None:
            continue
        await repo.crear_camarote(
            {
                "crucero_id": crucero_id,
                "tipo_camarote": tipo_camarote,
                "precio_por_persona": precio_num,
                # RF-CRU-006/CU-O123 — sintético, sin fuente real (ver
                # docstring del módulo): mismo criterio de honestidad que
                # tarifas_vuelo/actividades_horarios.
                "cupos_disponibles": cupos_default,
                "fecha_actualizacion": ahora,
            }
        )
        creados += 1
    return creados


async def generar_catalogo(client: CruisePricingClient, limite: int | None = None) -> dict:
    repo = CrucerosRepository()

    if limite is None:
        valor = await repo.config("cruceros.limite_cruceros")
        limite = int(valor) if valor else LIMITE_CRUCEROS_DEFAULT
    cupos_valor = await repo.config("disponibilidad_cruceros.cupos_default")
    cupos_default = int(cupos_valor) if cupos_valor else CUPOS_DEFAULT

    fuente = await repo.fuente_por_nombre("Cruise Pricing API")
    fecha_inicio = _ahora_iso()
    procesados = resueltos = 0
    error_detalle = None
    motivo_parcial = None

    try:
        navieras_lista = await client.listar_navieras()
        navieras_reales = {n["company"]: n for n in navieras_lista if n.get("company")}

        cruceros = await client.buscar_cruceros(limite)
        ahora = _ahora_iso()
        navieras_cache: dict[str, dict] = {}

        for resumen in cruceros:
            # RF-CRU-005 — gate real de cuota mensual (límite duro 100/mes,
            # plan Basic RapidAPI, corregido 2026-07-20: el supuesto previo
            # de ~500k/mes venía de headers de rate-limit mal interpretados
            # como techo mensual). Corta antes del siguiente `obtener_detalle`.
            if fuente and not await hay_cupo(
                fuente["id"], fuente.get("cuota_mensual_estimada"), getattr(client, "llamadas_realizadas", 0)
            ):
                motivo_parcial = "cuota_mensual_agotada"
                break
            procesados += 1
            cruise_id = resumen.get("cruise_id")
            company = resumen.get("company")
            ship_name = resumen.get("ship_name")
            if not cruise_id or not company or not ship_name:
                continue

            if company not in navieras_cache:
                navieras_cache[company] = await _asegurar_naviera(repo, company, navieras_reales, ahora)
            naviera = navieras_cache[company]
            barco = await _asegurar_barco(repo, naviera["id"], ship_name, ahora)

            detalle = await client.obtener_detalle(str(cruise_id))
            crucero_data = {
                "naviera_id": naviera["id"],
                "barco_id": barco["id"],
                "fuente_cruise_id": str(cruise_id),
                "fecha_zarpe": resumen.get("departure_date"),
                "duracion_dias": _num(resumen.get("duration")),
                "itinerario_puertos": resumen.get("ports_list") or [],
                "precio_base": _num(resumen.get("price"), 0.0),
                "moneda": resumen.get("currency") or "USD",
                "fecha_actualizacion": ahora,
            }

            existente = await repo.crucero_por_fuente_cruise_id(str(cruise_id))
            crucero = (
                await repo.actualizar_crucero(existente["id"], crucero_data)
                if existente
                else await repo.crear_crucero(crucero_data)
            )

            precios_camarote = detalle.get("cabin_prices_per_person") or {}
            await _generar_camarotes(repo, crucero["id"], cupos_default, precios_camarote)
            resueltos += 1

        estado = "exitoso" if resueltos > 0 else "parcial"
    except Exception as exc:  # noqa: BLE001 — se registra en la bitácora, no se oculta
        estado = "fallido"
        error_detalle = str(exc)

    if fuente:
        await repo.crear_log_sincronizacion(
            {
                "fuente_id": fuente["id"],
                "tipo_producto": "crucero",
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

    resumen_final = {"procesados": procesados, "resueltos": resueltos, "estado": estado}
    if motivo_parcial:
        resumen_final["motivo_parcial"] = motivo_parcial
    if error_detalle:
        resumen_final["error_detalle"] = error_detalle
    print(f"[CRUCEROS] {resumen_final}")
    return resumen_final
