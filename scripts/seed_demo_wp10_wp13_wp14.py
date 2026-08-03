"""Datos semisintéticos para que los paneles nuevos de la auditoría de
WorkPanels (2026-07-31) tengan algo real que mostrar en capturas/demo:
WP-10 (Proveedores comerciales), WP-13 (Comisiones), WP-14 (Remesas a
proveedores). No reemplaza datos reales — solo agrega variedad donde hoy
está vacío. Idempotente por clave natural en cada bloque.

Ejecutar: python scripts/seed_demo_wp10_wp13_wp14.py
"""

import asyncio
import datetime
import sys

sys.path.insert(0, ".")

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.proveedores.repositories.proveedores_repo import ProveedoresRepository
from app.vuelos.repositories.vuelos_repo import VuelosRepository

PROVEEDORES_DEMO = [
    {"nombre": "Marriott International", "tipo_producto": "hotel", "comision_pactada_pct": 12.0,
     "contacto": "partners@marriott-demo.test", "fecha_contrato": "2025-03-01"},
    {"nombre": "Hilton Worldwide", "tipo_producto": "hotel", "comision_pactada_pct": 11.5,
     "contacto": "corporate@hilton-demo.test", "fecha_contrato": "2025-06-15"},
    {"nombre": "Hertz Rent a Car", "tipo_producto": "auto", "comision_pactada_pct": 9.0,
     "contacto": "b2b@hertz-demo.test", "fecha_contrato": "2024-11-10"},
    {"nombre": "Avis Budget Group", "tipo_producto": "auto", "comision_pactada_pct": 8.5,
     "contacto": "ventas@avis-demo.test", "fecha_contrato": "2025-01-20"},
    {"nombre": "Viator Experiences", "tipo_producto": "actividad", "comision_pactada_pct": 15.0,
     "contacto": "partners@viator-demo.test", "fecha_contrato": "2025-08-05"},
    {"nombre": "GetYourGuide Tours", "tipo_producto": "actividad", "comision_pactada_pct": 14.0,
     "contacto": "affiliates@getyourguide-demo.test", "fecha_contrato": "2025-09-12"},
    {"nombre": "Holiday Inn Express", "tipo_producto": "hotel", "comision_pactada_pct": 10.0,
     "contacto": "regional@ihg-demo.test", "fecha_contrato": "2024-05-01", "activo": False},
]

# (aerolinea_nombre, cantidad_pendiente, cantidad_cobrada) — monto se deriva
# de una comisión pactada realista (5-6.5%) sobre un pago típico (150-650).
COMISIONES_POR_AEROLINEA = [
    ("Delta Air Lines", 3, 5),
    ("American Airlines", 2, 4),
    ("United Airlines", 2, 3),
    ("Alaska Airlines", 1, 2),
    ("Southwest Airlines", 2, 2),
]

MONTOS_DEMO = [18.5, 22.0, 27.75, 31.2, 14.9, 39.5, 45.0, 19.8, 24.3, 33.6]


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


async def seed_proveedores() -> None:
    repo = ProveedoresRepository()
    existentes = {p["nombre"] for p in await repo.listar()}
    creados = 0
    for data in PROVEEDORES_DEMO:
        if data["nombre"] in existentes:
            continue
        payload = {**data}
        payload.setdefault("activo", True)
        await repo.crear(payload)
        creados += 1
    print(f"+ proveedores comerciales: {creados} creados, {len(PROVEEDORES_DEMO) - creados} ya existían")


async def seed_comisiones_y_remesas() -> tuple[list[str], list[str]]:
    fact_repo = FacturacionRepository()
    vuelos_repo = VuelosRepository()
    aerolineas = {a["nombre"]: a for a in await vuelos_repo.listar_aerolineas_activas()}

    comisiones_existentes = await fact_repo.listar_comisiones()
    # Idempotencia simple: si ya hay comisiones marcadas con el prefijo de
    # monto usado acá para AL MENOS 3 aerolíneas, asumimos que el seed ya
    # corrió y no duplicamos.
    aerolineas_con_demo = {
        c["aerolinea_id"] for c in comisiones_existentes if c.get("monto") in MONTOS_DEMO
    }
    if len(aerolineas_con_demo) >= 3:
        print("= comisiones demo: ya sembradas, se omite")
        return [], []

    monto_idx = 0
    comision_ids: list[str] = []
    # (aerolinea_id, monto, comision_id) de las que quedan "cobrada" — para
    # armar la remesa histórica de Delta sin volver a consultar la API.
    cobradas_delta: list[tuple[float, str]] = []
    delta = aerolineas.get("Delta Air Lines")

    for nombre_aerolinea, n_pendientes, n_cobradas in COMISIONES_POR_AEROLINEA:
        aerolinea = aerolineas.get(nombre_aerolinea)
        if aerolinea is None:
            print(f"  ! aerolínea '{nombre_aerolinea}' no encontrada — saltando")
            continue
        for _ in range(n_pendientes):
            monto = MONTOS_DEMO[monto_idx % len(MONTOS_DEMO)]
            monto_idx += 1
            c = await fact_repo.crear_comision(
                {"reserva_id": "", "aerolinea_id": aerolinea["id"], "monto": monto, "estado": "pendiente_cobro"}
            )
            comision_ids.append(c["id"])
        for _ in range(n_cobradas):
            monto = MONTOS_DEMO[monto_idx % len(MONTOS_DEMO)]
            monto_idx += 1
            c = await fact_repo.crear_comision(
                {
                    "reserva_id": "", "aerolinea_id": aerolinea["id"], "monto": monto, "estado": "cobrada",
                    "fecha_cobro_real": _timestamp(),
                }
            )
            comision_ids.append(c["id"])
            if delta is not None and aerolinea["id"] == delta["id"]:
                cobradas_delta.append((monto, c["id"]))
    print(f"+ comisiones demo: {len(comision_ids)} creadas")

    # Remesas: una pagada (histórica) para Delta, dejando adrede el resto
    # de las aerolíneas con comisiones "cobrada, sin remesa" para poder
    # generar una remesa nueva desde la UI durante la demo.
    remesa_ids: list[str] = []
    if cobradas_delta:
        elegidas = cobradas_delta[:2]
        monto_total = round(sum(m for m, _ in elegidas), 2)
        remesa = await fact_repo.crear_remesa(
            {
                "aerolinea_id": delta["id"], "periodo": "2026-06", "monto_total": monto_total,
                "estado": "pagada", "fecha_generacion": "2026-07-05 00:00:00.000Z",
            }
        )
        for _, cid in elegidas:
            await fact_repo.agregar_remesa_comision(remesa["id"], cid)
        remesa_ids.append(remesa["id"])
        print("+ remesa demo (pagada, histórica) para Delta Air Lines")

    return comision_ids, remesa_ids


async def main() -> None:
    await seed_proveedores()
    await seed_comisiones_y_remesas()
    print("Listo.")


if __name__ == "__main__":
    asyncio.run(main())
