"""Gate de cuota mensual real para fuentes con techo duro documentado
(plan Basic de RapidAPI: HotelLens 100/mes, Global Rental Cars 100/mes,
Travel Advisor 500/mes — confirmado en el panel real de RapidAPI, no en
pruebas sin 429). No se mantiene un contador mutable aparte — se deriva de
`sincronizaciones_log.unidades_cuota_consumidas` (ya es la fuente de verdad,
una fila por corrida), sumando lo consumido desde el 1° del mes en curso.
"""

import datetime

from app.shared.pocketbase_client import get_pocketbase_client

MARGEN_SEGURIDAD_DEFAULT = 0.85


async def unidades_usadas_este_mes(fuente_id: str, hoy: datetime.datetime | None = None) -> int:
    client = get_pocketbase_client()
    ahora = hoy or datetime.datetime.now(datetime.timezone.utc)
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    resultado = await client.list_records(
        "sincronizaciones_log",
        {
            "filter": f'fuente_id="{fuente_id}" && fecha_inicio >= "{inicio_mes.strftime("%Y-%m-%d %H:%M:%S.000Z")}"',
            "perPage": 200,
        },
    )
    return sum(item.get("unidades_cuota_consumidas") or 0 for item in resultado["items"])


async def hay_cupo(
    fuente_id: str,
    cuota_mensual: float | None,
    ya_gastadas_en_esta_corrida: int,
    margen: float = MARGEN_SEGURIDAD_DEFAULT,
) -> bool:
    """`cuota_mensual` None = sin techo mensual real confirmado (ej. Cruise
    Pricing, ~500k/mes) — no gatea, siempre True. Si hay techo real, deja un
    colchón (`margen`) para absorber el sobregasto de la ciudad en curso
    (el chequeo es ANTES de empezar una ciudad nueva, no llamada a llamada)."""
    if not cuota_mensual:
        return True
    usadas_antes = await unidades_usadas_este_mes(fuente_id)
    return (usadas_antes + ya_gastadas_en_esta_corrida) < (cuota_mensual * margen)


# ── Gate de cuota DIARIA (llamadas en vivo, por interacción de usuario —
# Places/Geocoding/Routes de Google Cloud, sin un "run" de catálogo que
# loguee en sincronizaciones_log) — mismo patrón que ya usa AviationStack
# (`app/disrupciones/integrations/flight_status_client.py:54-132`,
# `_config()`/`esta_disponible()`/`_incrementar_contador()`), generalizado
# a un `prefijo` de configuracion_sistema reutilizable por cualquier
# integración con techo diario real.


async def cupo_diario_disponible(prefijo: str, margen: float = MARGEN_SEGURIDAD_DEFAULT) -> bool:
    """Lee `{prefijo}.limite_diario`/`.usadas_dia`/`.periodo_actual`
    (YYYY-MM-DD) de `configuracion_sistema`. Sin `limite_diario` sembrado
    (o vacío) = sin techo real confirmado, no gatea. Si el día cambió desde
    `.periodo_actual`, resetea el contador antes de comparar — mismo
    auto-reset por período que `api_estado_vuelo.periodo_actual`, pero por
    día en vez de por mes."""
    client = get_pocketbase_client()
    limite_reg = await client.get_first("configuracion_sistema", f'clave="{prefijo}.limite_diario"')
    if limite_reg is None or not limite_reg.get("valor"):
        return True

    periodo_reg = await client.get_first("configuracion_sistema", f'clave="{prefijo}.periodo_actual"')
    usadas_reg = await client.get_first("configuracion_sistema", f'clave="{prefijo}.usadas_dia"')
    if periodo_reg is None or usadas_reg is None:
        return True  # no sembrado del todo -> mismo criterio permisivo que AviationStack

    hoy_str = datetime.date.today().isoformat()
    if periodo_reg["valor"] != hoy_str:
        await client.update_record("configuracion_sistema", periodo_reg["id"], {"valor": hoy_str})
        await client.update_record("configuracion_sistema", usadas_reg["id"], {"valor": "0"})
        usadas = 0
    else:
        usadas = int(usadas_reg["valor"] or 0)

    limite = int(limite_reg["valor"])
    return usadas < (limite * margen)


async def registrar_uso_diario(prefijo: str) -> None:
    """Incrementa `{prefijo}.usadas_dia` en 1 — llamar solo tras una
    llamada real exitosa (mismo criterio que `_incrementar_contador` de
    AviationStack: nunca se incrementa en un fallo ni en un chequeo)."""
    client = get_pocketbase_client()
    usadas_reg = await client.get_first("configuracion_sistema", f'clave="{prefijo}.usadas_dia"')
    if usadas_reg is None:
        return
    actuales = int(usadas_reg["valor"] or 0)
    await client.update_record("configuracion_sistema", usadas_reg["id"], {"valor": str(actuales + 1)})
