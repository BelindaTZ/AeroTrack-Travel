"""Tests de app/vuelos/services/aerodatabox_client.py — solo la función
pura de normalización (el parseo HTTP real del cliente concreto se
verifica en vivo, no con mocks de httpx, mismo criterio que el resto del
proyecto: los `*ApiClient` son wrappers delgados, la lógica de negocio se
prueba a través del doble determinista en test_enriquecimiento_service.py)."""

from app.vuelos.services.aerodatabox_client import normalizar_numero_vuelo


def test_normalizar_numero_vuelo_quita_espacio_interno():
    assert normalizar_numero_vuelo("DL 466") == "DL466"


def test_normalizar_numero_vuelo_ya_sin_espacio_no_cambia():
    assert normalizar_numero_vuelo("DL466") == "DL466"


def test_normalizar_numero_vuelo_vacio():
    assert normalizar_numero_vuelo("") == ""
    assert normalizar_numero_vuelo(None) == ""
