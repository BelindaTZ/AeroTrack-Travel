"""RF-AUT-004 (CU-O119) — genera `autos_catalogo` desde Global Rental Cars
(sub-proveedor Expedia). Cada corrida se registra en `sincronizaciones_log`
(Integraciones, no dueño de esta colección — solo se escribe).

RNF-AUT-002: esta función solo escribe en `autos_catalogo` — nunca toca
`proveedores_comerciales` más allá de leerlo (no se resuelve comisión en
esta fase, mismo criterio que Hoteles Fase 1).
"""

import datetime

from app.autos.repositories.autos_repo import AutosRepository
from app.autos.services.rentalcars_client import RentalCarsClient, extraer_transmision, parsear_precio
from app.shared.cuota_service import hay_cupo
from app.shared.rotacion_ciudades import rebanada_rotativa

CIUDADES_DEFAULT = ["Paris", "Madrid", "New York"]
PROVEEDOR_AGREGADOR = "expedia"
CIUDADES_POR_CORRIDA_DEFAULT = 2


def _ahora_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z")


def _limpiar_modelo(descripcion: str | None) -> str:
    if not descripcion:
        return ""
    return descripcion.replace(" or similar", "").strip()


def _tarjeta_a_auto(card: dict, ciudad: str, codigo_ciudad: str, ahora: str) -> dict | None:
    vehicle = card.get("vehicle") or {}
    price_summary = card.get("priceSummary") or {}
    precio_dia = parsear_precio((price_summary.get("lead") or {}).get("formattedValue"))
    if precio_dia is None:
        return None  # sin precio real, no hay oferta que catalogar

    mensajes = [m.get("value", "") for m in (card.get("actionableConfidenceMessages") or [])]
    modalidad = "pagar_al_recoger" if any("Pay at pick-up" in m for m in mensajes) else "pagar_ahora"

    return {
        "proveedor_agregador": PROVEEDOR_AGREGADOR,
        "marca": "",  # el proveedor no separa marca de modelo, ver _limpiar_modelo
        "modelo": _limpiar_modelo(vehicle.get("description")),
        "categoria": vehicle.get("category") or "",
        "transmision": extraer_transmision(vehicle.get("attributes") or []),
        "ciudad_recogida": ciudad,
        "aeropuerto_codigo": codigo_ciudad,
        "precio_dia": precio_dia,
        "moneda": "USD",
        "modalidad_pago_disponible": modalidad,
        "fuente_oferta_ref": (card.get("detailsContext") or {}).get("carOfferToken"),
        "fecha_actualizacion": ahora,
    }


async def generar_catalogo(client: RentalCarsClient, ciudades: list[str] | None = None) -> dict:
    repo = AutosRepository()

    if ciudades is None:
        valor = await repo.config("autos.ciudades_seed")
        universo = [c.strip() for c in valor.split(",")] if valor else CIUDADES_DEFAULT
        valor_corrida = await repo.config("autos.ciudades_por_corrida")
        ciudades_por_corrida = int(valor_corrida) if valor_corrida else CIUDADES_POR_CORRIDA_DEFAULT
        # RF-AUT-004 — rotación determinística por día-del-año: da variedad
        # de ciudades entre corridas. La protección real contra el límite
        # duro real de Global Rental Cars (100 req/mes, plan Basic RapidAPI)
        # es el gate de app/shared/cuota_service.py más abajo.
        ciudades = rebanada_rotativa(universo, ciudades_por_corrida)

    fuente = await repo.fuente_por_nombre("Global Rental Cars")
    fecha_inicio = _ahora_iso()
    procesados = creados = 0
    error_detalle = None
    motivo_parcial = None

    try:
        for ciudad in ciudades:
            if fuente and not await hay_cupo(
                fuente["id"], fuente.get("cuota_mensual_estimada"), getattr(client, "llamadas_realizadas", 0)
            ):
                motivo_parcial = "cuota_mensual_agotada"
                break
            codigo = await client.resolver_codigo_ciudad(ciudad)
            if not codigo:
                continue

            tarjetas = await client.buscar_autos(codigo)
            ahora = _ahora_iso()
            # RN-AUT-001: snapshot point-in-time — se reemplaza completo por
            # ciudad+agregador en cada corrida, no se acumulan ofertas viejas.
            await repo.eliminar_ofertas_de_ciudad(ciudad, PROVEEDOR_AGREGADOR)

            for tarjeta in tarjetas:
                procesados += 1
                auto_data = _tarjeta_a_auto(tarjeta, ciudad, codigo, ahora)
                if auto_data is None:
                    continue
                await repo.crear_auto(auto_data)
                creados += 1
        estado = "exitoso" if creados > 0 else "parcial"
    except Exception as exc:  # noqa: BLE001 — se registra en la bitácora, no se oculta
        estado = "fallido"
        error_detalle = str(exc)

    if fuente:
        await repo.crear_log_sincronizacion(
            {
                "fuente_id": fuente["id"],
                "tipo_producto": "auto",
                "fecha_inicio": fecha_inicio,
                "fecha_fin": _ahora_iso(),
                "estado": estado,
                "registros_procesados": procesados,
                "registros_nuevos": creados,
                "registros_actualizados": 0,
                "unidades_cuota_consumidas": getattr(client, "llamadas_realizadas", 0),
                "error_detalle": error_detalle,
            }
        )

    resumen = {"ciudades": ciudades, "procesados": procesados, "creados": creados, "estado": estado}
    if motivo_parcial:
        resumen["motivo_parcial"] = motivo_parcial
    if error_detalle:
        resumen["error_detalle"] = error_detalle
    print(f"[AUTOS] {resumen}")
    return resumen
