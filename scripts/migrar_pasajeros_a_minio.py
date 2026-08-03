"""Migración única: copia `pasajeros`, `documentos_viaje` y
`viajeros_frecuentes` de pocketbase-travel al bucket operacional de MinIO
(`aerotrack-travel-operational`), como parte del plan de migración de
arquitectura (PocketBase pasa a ser staging/config; estas 3 colecciones son
OPERACIONAL y se leen/escriben desde ahí en adelante vía
`app/pasajeros/repositories/pasajeros_repo.py`).

Idempotente: si un id ya existe en MinIO, se omite (no sobreescribe).
Correr una sola vez antes de depender del código migrado en producción;
en este entorno de desarrollo ya se corrió contra los datos reales de
pocketbase-travel (ver memoria de la sesión).
"""

import asyncio

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import get_pocketbase_client

COLECCIONES = ["pasajeros", "documentos_viaje", "viajeros_frecuentes"]


async def _migrar_coleccion(nombre: str) -> tuple[int, int]:
    pb = get_pocketbase_client()
    migrados, ya_existian = 0, 0
    pagina = 1
    while True:
        resultado = await pb.list_records(nombre, {"page": pagina, "perPage": 200})
        for registro in resultado["items"]:
            try:
                await moc.crear(nombre, registro["id"], registro)
                migrados += 1
            except moc.RegistroYaExiste:
                ya_existian += 1
        if pagina >= resultado.get("totalPages", 1):
            break
        pagina += 1
    return migrados, ya_existian


async def main() -> None:
    for nombre in COLECCIONES:
        migrados, ya_existian = await _migrar_coleccion(nombre)
        print(f"{nombre}: {migrados} migrados, {ya_existian} ya existían en MinIO")


if __name__ == "__main__":
    asyncio.run(main())
