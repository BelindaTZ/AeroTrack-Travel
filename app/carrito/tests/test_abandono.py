"""CU-T26/T27 (RF-CAR-T01/T02) — detección de abandono, RN-CAR-T01
(convertido nunca cambia), recuperación vía `carrito_de_trabajo`, y
reporte de tasa de recuperación (RN-CAR-T02)."""

import datetime

import pytest

from app.carrito.repositories.carrito_repo import CarritoRepository
from app.carrito.services.abandono_service import marcar_abandonados_y_notificar
from app.carrito.services.reporte_abandono_service import reporte_recuperacion
from app.disrupciones.integrations.notification_sender import NotificationSender
from app.shared import minio_operational_client as moc


class NotificationSenderFalso(NotificationSender):
    def __init__(self, exitoso: bool = True):
        self.exitoso = exitoso
        self.enviados: list[dict] = []

    async def enviar(self, canal: str, destino: str, asunto: str, cuerpo: str) -> bool:
        self.enviados.append({"canal": canal, "destino": destino, "asunto": asunto, "cuerpo": cuerpo})
        return self.exitoso


def _iso(momento: datetime.datetime) -> str:
    return momento.strftime("%Y-%m-%d %H:%M:%S.000Z")


@pytest.fixture
async def carrito_factory():
    creados: list[str] = []

    async def _crear(pasajero_id: str, estado: str = "activo", horas_inactivo: float = 0.0, **extra) -> dict:
        ahora = datetime.datetime.now(datetime.timezone.utc)
        actividad = ahora - datetime.timedelta(hours=horas_inactivo)
        data = {
            "pasajero_id": pasajero_id, "estado": estado,
            "fecha_creacion": _iso(actividad), "fecha_ultima_actividad": _iso(actividad),
        }
        data.update(extra)
        carrito = await CarritoRepository().crear_carrito(data)
        creados.append(carrito["id"])
        return carrito

    yield _crear

    for carrito_id in creados:
        try:
            await moc.eliminar("carritos", carrito_id)
        except Exception:
            pass


async def test_marca_abandonado_un_carrito_activo_inactivo_y_envia_email(pasajero_factory, carrito_factory):
    # No se asume una base de datos vacía (puede haber otros carritos
    # `activo` inactivos reales/de otras pruebas) — se valida por el
    # registro propio, no por el conteo global de `marcados`.
    usuario, pasajero = await pasajero_factory()
    carrito = await carrito_factory(pasajero["id"], estado="activo", horas_inactivo=5)

    sender = NotificationSenderFalso()
    ahora = datetime.datetime.now(datetime.timezone.utc)
    marcados = await marcar_abandonados_y_notificar(sender, ahora=ahora)

    assert marcados >= 1
    repo = CarritoRepository()
    actualizado = await repo.obtener_carrito(carrito["id"])
    assert actualizado["estado"] == "abandonado"
    assert actualizado["fue_abandonado"] is True
    assert actualizado["fecha_marcado_abandonado"]
    envio_propio = next((e for e in sender.enviados if e["destino"] == usuario["email"]), None)
    assert envio_propio is not None
    assert envio_propio["canal"] == "email"


async def test_carrito_activo_reciente_no_se_marca(pasajero_factory, carrito_factory):
    _, pasajero = await pasajero_factory()
    carrito = await carrito_factory(pasajero["id"], estado="activo", horas_inactivo=0.01)

    sender = NotificationSenderFalso()
    marcados = await marcar_abandonados_y_notificar(sender)

    repo = CarritoRepository()
    actualizado = await repo.obtener_carrito(carrito["id"])
    assert actualizado["estado"] == "activo"
    assert marcados == 0 or actualizado["id"] != carrito["id"]


async def test_carrito_convertido_nunca_se_marca_abandonado(pasajero_factory, carrito_factory):
    """RN-CAR-T01 — sin importar cuánto tiempo lleve inactivo tras
    convertirse, un carrito `convertido` nunca pasa a `abandonado`."""
    _, pasajero = await pasajero_factory()
    carrito = await carrito_factory(pasajero["id"], estado="convertido", horas_inactivo=100)

    sender = NotificationSenderFalso()
    await marcar_abandonados_y_notificar(sender)

    repo = CarritoRepository()
    actualizado = await repo.obtener_carrito(carrito["id"])
    assert actualizado["estado"] == "convertido"
    assert not sender.enviados


async def test_fallo_de_envio_no_impide_marcar_abandonado(pasajero_factory, carrito_factory):
    _, pasajero = await pasajero_factory()
    carrito = await carrito_factory(pasajero["id"], estado="activo", horas_inactivo=5)

    class SenderCaido(NotificationSender):
        async def enviar(self, canal, destino, asunto, cuerpo):
            raise RuntimeError("proveedor caído")

    marcados = await marcar_abandonados_y_notificar(SenderCaido())

    assert marcados == 1
    repo = CarritoRepository()
    actualizado = await repo.obtener_carrito(carrito["id"])
    assert actualizado["estado"] == "abandonado"


async def test_carrito_de_trabajo_reactiva_uno_abandonado(pasajero_factory, carrito_factory):
    """Sin esta reactivación, un carrito abandonado nunca podría completar
    checkout ni contar como recuperado en CU-T27."""
    _, pasajero = await pasajero_factory()
    carrito = await carrito_factory(pasajero["id"], estado="abandonado", fue_abandonado=True)

    repo = CarritoRepository()
    de_trabajo = await repo.carrito_de_trabajo(pasajero["id"])

    assert de_trabajo["id"] == carrito["id"]
    assert de_trabajo["estado"] == "activo"


async def test_carrito_de_trabajo_ignora_convertido(pasajero_factory, carrito_factory):
    _, pasajero = await pasajero_factory()
    await carrito_factory(pasajero["id"], estado="convertido")

    repo = CarritoRepository()
    de_trabajo = await repo.carrito_de_trabajo(pasajero["id"])
    assert de_trabajo is None


async def test_reporte_cuenta_recuperados_y_no_recuperados(pasajero_factory, carrito_factory):
    # Deltas antes/después, no totales absolutos — no se asume una base de
    # datos vacía de otros carritos `fue_abandonado=true` reales/de otras
    # pruebas dentro de la misma ventana de 30 días.
    antes = await reporte_recuperacion(dias=30)

    _, pasajero_a = await pasajero_factory()
    _, pasajero_b = await pasajero_factory()
    _, pasajero_c = await pasajero_factory()

    ahora_iso = _iso(datetime.datetime.now(datetime.timezone.utc))
    # Abandonado y nunca recuperado.
    await carrito_factory(pasajero_a["id"], estado="abandonado", fue_abandonado=True, fecha_marcado_abandonado=ahora_iso)
    # Abandonado y luego recuperado (convertido).
    await carrito_factory(pasajero_b["id"], estado="convertido", fue_abandonado=True, fecha_marcado_abandonado=ahora_iso)
    # Convertido sin haber pasado nunca por abandono — no participa (RN-CAR-T02).
    await carrito_factory(pasajero_c["id"], estado="convertido", fue_abandonado=False)

    despues = await reporte_recuperacion(dias=30)

    assert despues["total_abandonados"] - antes["total_abandonados"] == 2
    assert despues["recuperados"] - antes["recuperados"] == 1


async def test_reporte_periodo_excluye_marcados_fuera_de_rango(pasajero_factory, carrito_factory):
    antes = await reporte_recuperacion(dias=30)

    _, pasajero = await pasajero_factory()
    hace_60_dias = _iso(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=60))
    await carrito_factory(pasajero["id"], estado="abandonado", fue_abandonado=True, fecha_marcado_abandonado=hace_60_dias)

    despues = await reporte_recuperacion(dias=30)
    assert despues["total_abandonados"] == antes["total_abandonados"]
