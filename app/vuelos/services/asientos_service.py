"""RF-VUE-011/012/013 (CU-O115/116/117) — mapa de asientos, selección y
asignación automática.

No hay fuente externa de mapas de asiento reales (RF-VUE-011: "generado por
el mismo job de catálogo como regla de negocio") — el layout es una fórmula
fija (30 filas, A-F, 3-3), no un dato importado. Los 3 parámetros de negocio
(recargo premium, proporción de filas premium, ventana de check-in gratis)
se leen de `configuracion_sistema.disponibilidad_asientos.*` con fallback a
un default en código — RN-VUE-T03: eso es explícitamente suficiente hasta
que el nivel Táctico (CU-T39/T40) tenga su propia UI de administración, no
es un placeholder a medias.
"""

import asyncio
import datetime
from collections import defaultdict

from app.reservas.repositories.reservas_repo import ReservasRepository
from app.vuelos.repositories.vuelos_repo import VuelosRepository

FILAS = 30
COLUMNAS = ["A", "B", "C", "D", "E", "F"]
VENTANA = {"A": "ventana", "F": "ventana", "C": "pasillo", "D": "pasillo", "B": "medio", "E": "medio"}

DEFAULT_RECARGO_PREMIUM = 15.0
DEFAULT_PCT_FILAS_PREMIUM = 0.15
DEFAULT_HORAS_CHECKIN_GRATIS = 36.0

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class AsientoNoValido(Exception):
    """El asiento no existe o no pertenece a este vuelo."""


class AsientoNoDisponible(Exception):
    """Ya fue tomado por otro pasajero."""


class SeleccionNoPermitidaAun(Exception):
    """Tarifa Light, asiento estándar, fuera de la ventana de check-in gratis."""


def _parse_fecha_pb(valor: str) -> datetime.datetime:
    return datetime.datetime.strptime(valor[:19], "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=datetime.timezone.utc
    )


async def _config_float(repo: VuelosRepository, clave: str, default: float) -> float:
    valor = await repo.config(f"disponibilidad_asientos.{clave}")
    if valor is None:
        return default
    try:
        return float(valor)
    except ValueError:
        return default


_GENERACION_CONCURRENCIA = 20  # cada create_record abre su propia conexión HTTP —
# 180 en serie tardaban ~90s reales (verificado con la suite); en paralelo (acotado
# para no saturar PocketBase/SQLite) queda en el orden de segundos.


async def obtener_o_generar_mapa(vuelo_id: str, repo: VuelosRepository | None = None) -> list[dict]:
    repo = repo or VuelosRepository()
    existentes = await repo.asientos_de_vuelo(vuelo_id)
    if existentes:
        return existentes

    # Lock por vuelo (prefijo para no compartir namespace con los locks de
    # reserva/liberación de asiento, que usan asiento_id como clave): sin
    # esto, dos requests concurrentes viendo el mapa vacío generarían 360
    # asientos duplicados en vez de 180.
    async with _locks[f"mapa:{vuelo_id}"]:
        existentes = await repo.asientos_de_vuelo(vuelo_id)
        if existentes:
            return existentes
        return await _generar_mapa(vuelo_id, repo)


async def _generar_mapa(vuelo_id: str, repo: VuelosRepository) -> list[dict]:
    recargo_premium = await _config_float(repo, "recargo_premium", DEFAULT_RECARGO_PREMIUM)
    pct_premium = await _config_float(repo, "pct_filas_premium", DEFAULT_PCT_FILAS_PREMIUM)
    filas_premium = max(1, round(FILAS * pct_premium))

    payloads = [
        {
            "vuelo_id": vuelo_id,
            "fila": fila,
            "columna": columna,
            "tipo_asiento": VENTANA[columna],
            "es_premium": fila <= filas_premium,
            "recargo": recargo_premium if fila <= filas_premium else 0.0,
            "disponible": True,
        }
        for fila in range(1, FILAS + 1)
        for columna in COLUMNAS
    ]

    semaforo = asyncio.Semaphore(_GENERACION_CONCURRENCIA)

    async def _crear(payload: dict) -> dict:
        async with semaforo:
            return await repo.crear_asiento(payload)

    return list(await asyncio.gather(*(_crear(p) for p in payloads)))


async def ventana_checkin_abierta(repo: VuelosRepository, vuelo: dict, ahora: datetime.datetime) -> bool:
    horas = await _config_float(repo, "horas_antes_checkin_gratis", DEFAULT_HORAS_CHECKIN_GRATIS)
    salida = _parse_fecha_pb(vuelo["fecha_salida"])
    return ahora >= salida - datetime.timedelta(hours=horas)


async def validar_y_reservar_asiento(
    vuelo: dict,
    nivel: dict,
    asiento_id: str,
    ahora: datetime.datetime | None = None,
    repo: VuelosRepository | None = None,
) -> dict:
    """RF-VUE-012 — valida la regla de ventana de check-in por tarifa y, si
    procede, marca el asiento como no disponible. Devuelve el asiento (con
    `es_premium`/`recargo`) para que el caller decida el cobro."""
    repo = repo or VuelosRepository()
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)

    async with _locks[asiento_id]:
        asiento = await repo.obtener_asiento(asiento_id)
        if asiento is None or asiento["vuelo_id"] != vuelo["id"]:
            raise AsientoNoValido()
        if not asiento.get("disponible", True):
            raise AsientoNoDisponible()

        if not asiento.get("es_premium"):
            # RF-VUE-012: Standard/Flex eligen asiento estándar desde ya;
            # Light solo cuando abre la ventana de check-in gratuito.
            if not nivel.get("seleccion_asiento_temprana"):
                if not await ventana_checkin_abierta(repo, vuelo, ahora):
                    raise SeleccionNoPermitidaAun()

        await repo.actualizar_asiento(asiento_id, {"disponible": False})
        return asiento


async def liberar_asiento(asiento_id: str | None, repo: VuelosRepository | None = None) -> None:
    if not asiento_id:
        return
    repo = repo or VuelosRepository()
    async with _locks[asiento_id]:
        asiento = await repo.obtener_asiento(asiento_id)
        if asiento is None:
            return
        await repo.actualizar_asiento(asiento_id, {"disponible": True})


async def liberar_asientos_de_reserva(reserva_id: str) -> None:
    """Cancelación/expiración (RN-RES-003/CU-O44) — sin esto, un asiento de
    una reserva cancelada quedaría bloqueado para siempre."""
    reservas_repo = ReservasRepository()
    for pasajero in await reservas_repo.pasajeros_de_reserva(reserva_id):
        if pasajero.get("asiento_id"):
            await liberar_asiento(pasajero["asiento_id"])


async def asignar_automaticamente(ahora: datetime.datetime | None = None) -> int:
    """RF-VUE-013 (CU-O117) — disparado por temporizador (análogo a CU-O44,
    ver `dags/dag_asignar_asientos.py`). Asigna, sin cargo, un asiento a
    todo pasajero confirmado sin elección propia cuya ventana de check-in ya
    abrió. Prefiere un asiento estándar; si no queda ninguno disponible,
    asigna el que sea (regla de negocio confirmada, no un bug: en vuelos
    llenos puede separar a un grupo que no eligió a tiempo)."""
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    reservas_repo = ReservasRepository()
    vuelos_repo = VuelosRepository()

    asignados = 0
    for pasajero in await reservas_repo.pasajeros_sin_asiento():
        reserva = await reservas_repo.obtener_reserva(pasajero["reserva_id"])
        if reserva is None or reserva["estado"] not in ("confirmada", "modificada"):
            continue
        vuelo_id = reserva.get("vuelo_id")
        if not vuelo_id:
            continue
        vuelo = await vuelos_repo.obtener_vuelo(vuelo_id)
        if vuelo is None or vuelo["estado"] not in ("programado", "retrasado"):
            continue
        if not await ventana_checkin_abierta(vuelos_repo, vuelo, ahora):
            continue

        asientos = await obtener_o_generar_mapa(vuelo_id, vuelos_repo)
        disponibles = [a for a in asientos if a.get("disponible")]
        if not disponibles:
            continue
        estandar = [a for a in disponibles if not a.get("es_premium")]
        elegido = estandar[0] if estandar else disponibles[0]

        async with _locks[elegido["id"]]:
            fresco = await vuelos_repo.obtener_asiento(elegido["id"])
            if fresco is None or not fresco.get("disponible"):
                continue  # otro proceso lo tomó entre el filtro y acá
            await vuelos_repo.actualizar_asiento(elegido["id"], {"disponible": False})

        await reservas_repo.actualizar_pasajero(
            pasajero["id"], {"asiento_id": elegido["id"], "asiento_asignado_por": "sistema"}
        )
        asignados += 1

    return asignados
