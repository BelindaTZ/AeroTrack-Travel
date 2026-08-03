"""Tests de app/vuelos/services/google_flights_client.py — funciones
puras: normalización de número de vuelo y el gotcha real documentado
(SerpApi puede devolver una ruta distinta a la pedida con
"status": "Success", ver docs/google-flights-serpapi-hallazgos.md)."""

from app.vuelos.services.google_flights_client import _ruta_coincide, normalizar_numero_vuelo

ITINERARIO_DIRECTO_OK = {
    "flights": [
        {
            "departure_airport": {"id": "ATL", "time": "2026-07-22 09:21"},
            "arrival_airport": {"id": "JFK", "time": "2026-07-22 11:50"},
            "flight_number": "DL 466",
        }
    ]
}

ITINERARIO_RUTA_DISTINTA = {
    # Caso real confirmado: pedir ATL->JFK con travel_class=4 devolvió ATL->DCA.
    "flights": [
        {
            "departure_airport": {"id": "ATL", "time": "2026-07-22 09:21"},
            "arrival_airport": {"id": "DCA", "time": "2026-07-22 10:40"},
            "flight_number": "DL 123",
        }
    ]
}

ITINERARIO_CON_ESCALA = {
    "flights": [
        {"departure_airport": {"id": "ATL"}, "arrival_airport": {"id": "ORD"}, "flight_number": "DL 1"},
        {"departure_airport": {"id": "ORD"}, "arrival_airport": {"id": "JFK"}, "flight_number": "DL 2"},
    ]
}


def test_normalizar_numero_vuelo_quita_espacio():
    assert normalizar_numero_vuelo("DL 466") == "DL466"


def test_ruta_coincide_con_itinerario_directo_correcto():
    assert _ruta_coincide(ITINERARIO_DIRECTO_OK, "ATL", "JFK") is True


def test_ruta_coincide_rechaza_ruta_distinta_a_la_pedida():
    """El gotcha real: SerpApi puede devolver otra ruta con status Success."""
    assert _ruta_coincide(ITINERARIO_RUTA_DISTINTA, "ATL", "JFK") is False


def test_ruta_coincide_rechaza_itinerarios_con_escala():
    """El modelo de datos del proyecto no tiene concepto de escalas."""
    assert _ruta_coincide(ITINERARIO_CON_ESCALA, "ATL", "JFK") is False


def test_ruta_coincide_itinerario_vacio():
    assert _ruta_coincide({}, "ATL", "JFK") is False
    assert _ruta_coincide({"flights": []}, "ATL", "JFK") is False
