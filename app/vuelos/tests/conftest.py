# Fixtures compartidas (client, pb, usuario_factory, vuelo_factory,
# tarifa_factory, pasajero_factory, admin_client, rol_administrador,
# rol_agente) viven en el conftest.py de la raíz del repo — pytest las
# descubre automáticamente, no requieren import aquí.
#
# Dobles deterministas de AeroDataBox/Google Flights — mismo criterio que
# app/hoteles/tests/conftest.py: la integración real ya se probó (o se
# probará) contra la API real, pero la suite automatizada no debe
# depender de cuota real en cada corrida.

import pytest

from app.vuelos.services.aerodatabox_client import AeroDataBoxClient
from app.vuelos.services.google_flights_client import GoogleFlightsClient


class AeroDataBoxClientFalso(AeroDataBoxClient):
    def __init__(self, salidas_por_hub: dict[str, list[dict]] | None = None):
        self.salidas_por_hub = salidas_por_hub or {}
        self.llamadas: list[str] = []

    async def salidas(self, codigo_aeropuerto: str, desde_local: str, hasta_local: str) -> list[dict]:
        self.llamadas.append(f"salidas:{codigo_aeropuerto}:{desde_local}:{hasta_local}")
        return self.salidas_por_hub.get(codigo_aeropuerto, [])


class GoogleFlightsClientFalso(GoogleFlightsClient):
    def __init__(self, resultados_por_ruta: dict[tuple[str, str], dict | None] | None = None):
        # Clave puede ser (origen, destino) — misma respuesta para las 3
        # clases, atajo para tests que no les importa la distinción — o
        # (origen, destino, clase) para canned answers por clase de cabina.
        self.resultados_por_ruta = resultados_por_ruta or {}
        self.llamadas: list[str] = []
        self.llamadas_realizadas = 0

    async def buscar(self, origen: str, destino: str, fecha: str, clase: str = "economy") -> dict | None:
        self.llamadas.append(f"buscar:{origen}:{destino}:{fecha}:{clase}")
        self.llamadas_realizadas += 1
        if (origen, destino, clase) in self.resultados_por_ruta:
            return self.resultados_por_ruta[(origen, destino, clase)]
        return self.resultados_por_ruta.get((origen, destino))


@pytest.fixture
def aerodatabox_falso():
    return AeroDataBoxClientFalso


@pytest.fixture
def google_flights_falso():
    return GoogleFlightsClientFalso
