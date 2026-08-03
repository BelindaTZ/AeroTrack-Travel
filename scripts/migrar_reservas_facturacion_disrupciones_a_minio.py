"""Migración única (paso 5 del plan): copia `reservas`, `reserva_items`,
`reserva_pasajeros`, `reserva_extras`, `alertas_precio`, `pagos`, `facturas`,
`comisiones`, `remesas`, `remesa_comisiones`, `reembolsos`, `disrupciones`,
`notificaciones`, `cupones_uso` de pocketbase-travel al bucket operacional
de MinIO. Idempotente — igual patrón que
`scripts/migrar_pasajeros_a_minio.py`.
"""

import asyncio

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import get_pocketbase_client

COLECCIONES = [
    "reservas", "reserva_items", "reserva_pasajeros", "reserva_extras", "alertas_precio",
    "pagos", "facturas", "comisiones", "remesas", "remesa_comisiones", "reembolsos",
    "disrupciones", "notificaciones", "cupones_uso",
]


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
