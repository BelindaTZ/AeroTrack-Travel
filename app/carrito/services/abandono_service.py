"""RF-CAR-T01 (CU-T26) — detecta carritos `activo` inactivos más allá del
umbral configurado, los marca `abandonado` y dispara el email de
recordatorio reutilizando la capa de envío real ya existente
(`app.disrupciones.integrations.notification_sender`, canal "email") en
vez de crear una vía nueva, tal como pide `carrito-spec.md`.

RN-CAR-T01: solo un carrito `activo` puede pasar a `abandonado`; uno
`convertido` nunca cambia — se revalida el estado justo antes de escribir
para no pisar una conversión concurrente entre la búsqueda y el update.

El envío de email puede fallar de verdad (credencial de Gmail OAuth con
scope de solo lectura, ver memoria del proyecto) — un fallo de envío
NUNCA debe impedir marcar el carrito abandonado ni detener el resto del
lote (mismo criterio que `disrupciones.services.notificacion_service`)."""

import datetime
import logging

from app.carrito.repositories.carrito_repo import CarritoRepository
from app.disrupciones.integrations.notification_sender import NotificationSender
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.seguridad.services.audit_service import AuditService

logger = logging.getLogger("carrito.abandono")

DEFAULT_UMBRAL_HORAS = 2.0
DEFAULT_ASUNTO = "¿Olvidaste algo en tu carrito?"
DEFAULT_CUERPO = (
    "Todavía tienes productos esperando en tu carrito de AeroTrack Travel. "
    "Vuelve para completar tu reserva antes de que se agote el cupo."
)


def _iso(momento: datetime.datetime) -> str:
    return momento.strftime("%Y-%m-%d %H:%M:%S.000Z")


async def _umbral_horas(repo: CarritoRepository) -> float:
    config = await repo.config("carrito_abandonado.umbral_horas_inactividad")
    if config is None:
        return DEFAULT_UMBRAL_HORAS
    try:
        return float(config["valor"])
    except (TypeError, ValueError):
        return DEFAULT_UMBRAL_HORAS


async def _plantilla(repo: CarritoRepository) -> tuple[str, str]:
    asunto = await repo.config("carrito_abandonado.plantilla_asunto")
    cuerpo = await repo.config("carrito_abandonado.plantilla_cuerpo")
    return (
        asunto["valor"] if asunto else DEFAULT_ASUNTO,
        cuerpo["valor"] if cuerpo else DEFAULT_CUERPO,
    )


async def _email_de_pasajero(pasajero_id: str) -> str | None:
    pasajeros_repo = PasajerosRepository()
    pasajero = await pasajeros_repo.obtener_pasajero(pasajero_id)
    if pasajero is None:
        return None
    usuario = await pasajeros_repo.usuario_por_id(pasajero["usuario_id"])
    return usuario["email"] if usuario else None


async def marcar_abandonados_y_notificar(
    sender: NotificationSender, ahora: datetime.datetime | None = None
) -> int:
    """CU-T26 — retorna la cantidad de carritos marcados `abandonado` en
    esta corrida."""
    repo = CarritoRepository()
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    umbral_horas = await _umbral_horas(repo)
    limite_iso = _iso(ahora - datetime.timedelta(hours=umbral_horas))

    candidatos = await repo.carritos_activos_inactivos_desde(limite_iso)
    if not candidatos:
        return 0

    asunto, cuerpo = await _plantilla(repo)
    ahora_iso = _iso(ahora)
    marcados = 0

    for carrito in candidatos:
        actual = await repo.obtener_carrito(carrito["id"])
        if actual is None or actual["estado"] != "activo":
            continue

        await repo.actualizar_carrito(
            carrito["id"],
            {"estado": "abandonado", "fue_abandonado": True, "fecha_marcado_abandonado": ahora_iso},
        )
        marcados += 1

        destino = await _email_de_pasajero(carrito["pasajero_id"])
        exitoso = False
        if destino:
            try:
                exitoso = await sender.enviar("email", destino, asunto, cuerpo)
            except Exception:
                logger.warning("Fallo al enviar email de carrito abandonado a %s", destino, exc_info=True)
                exitoso = False

        await AuditService().insertar(
            "marcar_carrito_abandonado",
            "carritos",
            registro_id=carrito["id"],
            detalle={"umbral_horas": umbral_horas, "email_enviado": exitoso},
        )

    return marcados
