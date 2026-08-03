"""Descarga de una sola vez ~6 fotos reales con licencia Unsplash (API ya
configurada en `.env`, nunca usada hasta ahora: `ACCESS_KEY`) para los
heroes de búsqueda (vuelos/hoteles/autos/actividades/cruceros) y la
sección de categorías de la home. Quedan como archivos estáticos en
`public/assets/images/` — mismo criterio que `login_hero.jpg`, no se
vuelve a llamar a Unsplash en cada carga de página.

Respeta los términos de la API de Unsplash: dispara el ping de
`links.download_location` de cada foto usada (requerido al usar una foto
fuera del sitio de Unsplash), no solo descarga el binario.

No idempotente a propósito — es un script de uso único; volver a correrlo
sobreescribe los archivos con una búsqueda nueva (puede traer fotos
distintas cada vez, es aceptable para este uso).

Ejecutar: python scripts/fetch_hero_images.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

ACCESS_KEY = os.environ.get("ACCESS_KEY", "")
BASE_URL = "https://api.unsplash.com"

DESTINO = "public/assets/images"

# (archivo, query de búsqueda, orientación)
FOTOS = [
    ("hero_vuelos.jpg", "airplane wing sky travel"),
    ("hero_hoteles.jpg", "hotel pool luxury resort"),
    ("hero_autos.jpg", "road trip car highway mountains"),
    ("hero_actividades.jpg", "city walking tour travelers"),
    ("hero_cruceros.jpg", "cruise ship ocean deck"),
    ("hero_home.jpg", "airport travel destination sunset"),
]


def buscar_foto(headers: dict, query: str) -> dict:
    resp = httpx.get(
        f"{BASE_URL}/search/photos",
        params={"query": query, "per_page": 1, "orientation": "landscape", "content_filter": "high"},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    resultados = resp.json().get("results") or []
    if not resultados:
        raise RuntimeError(f"Unsplash no devolvió resultados para '{query}'")
    return resultados[0]


def main() -> None:
    if not ACCESS_KEY:
        raise RuntimeError("ACCESS_KEY no está en el .env local — no se puede llamar a Unsplash")

    headers = {"Authorization": f"Client-ID {ACCESS_KEY}"}
    os.makedirs(DESTINO, exist_ok=True)

    for archivo, query in FOTOS:
        foto = buscar_foto(headers, query)
        url_imagen = foto["urls"]["regular"]  # ~1080px de ancho, buen balance calidad/peso
        autor = foto.get("user", {}).get("name", "desconocido")

        # Requerido por los términos de Unsplash al usar una foto fuera de su sitio.
        download_location = foto.get("links", {}).get("download_location")
        if download_location:
            httpx.get(download_location, headers=headers, timeout=15)

        imagen = httpx.get(url_imagen, timeout=30)
        imagen.raise_for_status()
        ruta = os.path.join(DESTINO, archivo)
        with open(ruta, "wb") as f:
            f.write(imagen.content)
        print(f"+ {archivo} <- '{query}' (foto de {autor} vía Unsplash) [{len(imagen.content) // 1024} KB]")

    print("Listo.")


if __name__ == "__main__":
    main()
