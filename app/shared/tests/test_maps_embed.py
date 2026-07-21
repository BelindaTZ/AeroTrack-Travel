"""Tests de app/shared/google_apis/maps_embed.py — funciones puras, sin
red ni PocketBase (Maps Embed nunca lo llama nuestro backend, lo carga el
navegador del usuario)."""

from app.shared.google_apis.maps_embed import url_mapa_punto, url_mapa_ruta


def test_url_mapa_punto_incluye_coordenadas_y_key():
    url = url_mapa_punto(48.8566, 2.3522, "clave-test")
    assert url.startswith("https://www.google.com/maps/embed/v1/place?")
    assert "key=clave-test" in url
    assert "q=48.8566%2C2.3522" in url


def test_url_mapa_ruta_con_dos_paradas_sin_waypoints():
    url = url_mapa_ruta(["Miami", "Nassau"], "clave-test")
    assert url is not None
    assert "origin=Miami" in url
    assert "destination=Nassau" in url
    assert "waypoints" not in url


def test_url_mapa_ruta_con_escalas_intermedias():
    url = url_mapa_ruta(["Miami", "Cozumel", "Nassau"], "clave-test")
    assert url is not None
    assert "origin=Miami" in url
    assert "destination=Nassau" in url
    assert "waypoints=Cozumel" in url


def test_url_mapa_ruta_con_menos_de_dos_paradas_devuelve_none():
    assert url_mapa_ruta([], "clave-test") is None
    assert url_mapa_ruta(["Miami"], "clave-test") is None


def test_url_mapa_ruta_ignora_paradas_vacias():
    url = url_mapa_ruta(["Miami", "", "Nassau"], "clave-test")
    assert url is not None
    assert "origin=Miami" in url
    assert "destination=Nassau" in url
