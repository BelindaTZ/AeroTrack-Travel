"""Verificación y liberación atómica de cupo — MIGRADO a MinIO operacional
(cierre de la deuda técnica identificada 2026-07-26: el mecanismo de
escritura condicional por ETag ya existía en `minio_operational_client`
desde el spike de concurrencia, pero cupo seguía decrementándose contra
PocketBase con un `asyncio.Lock` en memoria — correcto solo porque
`app-travel` corre como una sola instancia, y desconectado del mecanismo
que el resto del tier operacional ya usa).

`tarifas_vuelo`, `hoteles_tarifas`, `actividades_horarios`,
`cruceros_camarotes_tarifa` siguen siendo STAGING en PocketBase — su campo
`cupos_disponibles` queda congelado en el valor sembrado por el DAG/
catálogo de cada vertical y ya NUNCA se decrementa ahí. El cupo real vive
en MinIO, `operacional/cupos_{coleccion}/{id}.json`, con
`actualizar_con_reintento` (mismo mecanismo probado en el spike bajo carga
concurrente real).

Primer toque de cada registro: se siembra perezosamente desde el valor
STAGING vigente en PocketBase (`_asegurar_registro`) — ni el DAG de
catálogo de vuelos (`catalogo_vuelos_tasks.py`, que escribe PocketBase
directo) ni los `catalogo_service.py` de hoteles/actividades/cruceros
necesitan enterarse de que MinIO existe. Si el registro no tiene el campo
de cupo (p. ej. `autos_catalogo`, sin ese concepto), se trata como "sin
restricción" — no hay nada que verificar ni decrementar (mismo criterio
que la versión anterior).

`cupos_vigentes()` expone el valor real para overlay en búsqueda/detalle —
sin eso, esas vistas seguirían mostrando para siempre el valor STAGING
congelado en vez del cupo ya decrementado (ver routers de búsqueda de
vuelos/hoteles/actividades/cruceros).
"""

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client


def _entidad(coleccion: str) -> str:
    return f"cupos_{coleccion}"


async def _asegurar_registro(coleccion: str, registro_id: str, campo_cupo: str) -> bool:
    """True si ya existe (o se acaba de sembrar) un registro de cupo en
    MinIO para este ítem de catálogo. False si el ítem no existe en
    absoluto en PocketBase (staging) — nada que reservar/liberar.

    Sembrar dos veces en una carrera concurrente no es un problema: `crear`
    ya es atómico (`IfNoneMatch=*`) y el segundo intento simplemente
    encuentra `RegistroYaExiste` y sigue — no hace falta un lock adicional
    acá, la corrección la da MinIO, no el proceso de Python."""
    entidad = _entidad(coleccion)
    if await moc.obtener(entidad, registro_id) is not None:
        return True
    client = get_pocketbase_client()
    try:
        catalogo = await client.get_record(coleccion, registro_id)
    except PocketBaseError:
        return False
    try:
        await moc.crear(entidad, registro_id, {"id": registro_id, campo_cupo: catalogo.get(campo_cupo)})
    except moc.RegistroYaExiste:
        pass
    return True


async def verificar_y_reservar_cupo(
    coleccion: str, registro_id: str, campo_cupo: str = "cupos_disponibles", cantidad: int = 1
) -> bool:
    """Si hay cupo suficiente (o el registro no tiene ese campo), lo
    decrementa cuando aplica y devuelve True. Si no alcanza, no toca el
    dato y devuelve False. Registro inexistente también devuelve False."""
    if not await _asegurar_registro(coleccion, registro_id, campo_cupo):
        return False

    resultado = {"permitido": False}

    def _mutar(actual: dict) -> dict:
        disponibles = actual.get(campo_cupo)
        if disponibles is None:
            resultado["permitido"] = True  # la colección no modela cupo para este producto
            return actual
        if disponibles < cantidad:
            resultado["permitido"] = False
            return actual
        resultado["permitido"] = True
        actual[campo_cupo] = disponibles - cantidad
        return actual

    await moc.actualizar_con_reintento(_entidad(coleccion), registro_id, _mutar)
    return resultado["permitido"]


async def liberar_cupo(
    coleccion: str, registro_id: str, campo_cupo: str = "cupos_disponibles", cantidad: int = 1
) -> None:
    """Inversa de `verificar_y_reservar_cupo` — libera cupo al cancelar o
    expirar una reserva. Silenciosa si el ítem de catálogo ya no existe o
    no tiene ese campo (nada que liberar)."""
    if not await _asegurar_registro(coleccion, registro_id, campo_cupo):
        return

    def _mutar(actual: dict) -> dict:
        disponibles = actual.get(campo_cupo)
        if disponibles is None:
            return actual
        actual[campo_cupo] = disponibles + cantidad
        return actual

    await moc.actualizar_con_reintento(_entidad(coleccion), registro_id, _mutar)


async def cupos_vigentes(coleccion: str, campo_cupo: str = "cupos_disponibles") -> dict[str, int]:
    """`{registro_id: cupo_real}` de todo lo que ya se sembró/tocó en MinIO
    para esta colección — para overlay de disponibilidad real en listados
    de catálogo/detalle (que leen el snapshot NDJSON, congelado desde que
    este servicio dejó de escribir en PocketBase). Un id ausente acá
    todavía no fue tocado por ninguna reserva — el valor STAGING sigue
    siendo el correcto en ese caso, el llamador debe usarlo como fallback."""
    registros = await moc.listar_todos(_entidad(coleccion))
    return {r["id"]: r[campo_cupo] for r in registros if r.get(campo_cupo) is not None}
