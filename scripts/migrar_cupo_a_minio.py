"""Migración única: siembra en MinIO (`operacional/cupos_{coleccion}/`) el
`cupos_disponibles` vigente hoy en cada una de las 4 colecciones STAGING de
catálogo que modelan cupo real (`tarifas_vuelo`, `hoteles_tarifas`,
`actividades_horarios`, `cruceros_camarotes_tarifa`), como parte del cierre
de la deuda técnica de `app/shared/cupo_service.py` (2026-07-26).

No es estrictamente necesaria para que el sistema funcione — el propio
`cupo_service._asegurar_registro` siembra perezosamente cada registro en su
primer uso real — pero deja el tier operacional consistente desde el día 1
en vez de ir poblándose ítem por ítem según qué se reserve primero, y sirve
para verificar de un vistazo cuántos ítems de catálogo existen hoy.

Idempotente: si un id ya existe en MinIO, se omite (no sobreescribe un
cupo que ya pudo haber sido decrementado por una reserva real)."""

import asyncio

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import get_pocketbase_client

COLECCIONES = ["tarifas_vuelo", "hoteles_tarifas", "actividades_horarios", "cruceros_camarotes_tarifa"]
CAMPO_CUPO = "cupos_disponibles"


async def _migrar_coleccion(nombre: str) -> tuple[int, int, int]:
    pb = get_pocketbase_client()
    entidad = f"cupos_{nombre}"
    migrados, ya_existian, sin_campo = 0, 0, 0
    pagina = 1
    while True:
        resultado = await pb.list_records(nombre, {"page": pagina, "perPage": 200})
        for registro in resultado["items"]:
            if registro.get(CAMPO_CUPO) is None:
                sin_campo += 1
                continue
            try:
                await moc.crear(entidad, registro["id"], {"id": registro["id"], CAMPO_CUPO: registro[CAMPO_CUPO]})
                migrados += 1
            except moc.RegistroYaExiste:
                ya_existian += 1
        if pagina >= resultado.get("totalPages", 1):
            break
        pagina += 1
    return migrados, ya_existian, sin_campo


async def main() -> None:
    for nombre in COLECCIONES:
        migrados, ya_existian, sin_campo = await _migrar_coleccion(nombre)
        print(f"{nombre}: {migrados} sembrados, {ya_existian} ya existían en MinIO, {sin_campo} sin {CAMPO_CUPO}")


if __name__ == "__main__":
    asyncio.run(main())
