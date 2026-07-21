"""Fixtures propias de Disrupciones. `client`/`pb`/`usuario_factory`/
`vuelo_factory`/`tarifa_factory`/`pasajero_factory`/`reserva_factory`/
`admin_client`/`rol_administrador`/`rol_agente` viven en el conftest.py de
la raíz del repo — pytest las descubre automáticamente, no requieren import
aquí.

Los dobles de prueba de abajo NO reemplazan la verificación real de cada
integración — `flight_status_client.py`, `gmail_client.py` y
`notification_sender.py` ya se probaron una vez contra las APIs reales
(Fase 0, ver `errores-conocidos.md`: AviationStack y lectura de Gmail
funcionan de verdad; el envío falla por scope OAuth insuficiente, hallazgo
real, no simulado). Se usan aquí para que la suite sea determinística y no
gaste la cuota mensual real de AviationStack en cada corrida.
"""

import pytest

from app.disrupciones.integrations.flight_status_client import FlightStatusClient
from app.disrupciones.integrations.gmail_client import GmailClient
from app.disrupciones.integrations.notification_sender import NotificationSender


class FlightStatusClientFalso(FlightStatusClient):
    def __init__(self, disponible: bool = True, respuestas: dict | None = None):
        self.disponible = disponible
        self.respuestas = respuestas or {}
        self.llamadas: list[str] = []

    async def esta_disponible(self) -> bool:
        return self.disponible

    async def consultar_estado(self, numero_vuelo: str, fecha: str) -> dict | None:
        self.llamadas.append(numero_vuelo)
        if not self.disponible:
            raise ConnectionError("API de estado de vuelo no disponible (doble de prueba)")
        return self.respuestas.get(numero_vuelo)


class GmailClientFalso(GmailClient):
    def __init__(self, correos: list[dict] | None = None):
        self.correos = correos or []

    async def leer_correos_nuevos(self, ultimas_horas: int = 24) -> list[dict]:
        return self.correos


class NotificationSenderFalso(NotificationSender):
    def __init__(self, exitoso: bool = True):
        self.exitoso = exitoso
        self.enviados: list[dict] = []

    async def enviar(self, canal: str, destino: str, asunto: str, cuerpo: str) -> bool:
        self.enviados.append({"canal": canal, "destino": destino, "asunto": asunto, "cuerpo": cuerpo})
        return self.exitoso


@pytest.fixture
def flight_status_falso():
    return FlightStatusClientFalso


@pytest.fixture
def gmail_client_falso():
    return GmailClientFalso


@pytest.fixture
def notification_sender_falso():
    return NotificationSenderFalso()


@pytest.fixture
async def vuelo_con_reserva_confirmada(pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory(estado="programado")
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], estado="confirmada")
    return {"usuario": usuario, "pasajero": pasajero, "vuelo": vuelo, "tarifa": tarifa, "reserva": reserva}
