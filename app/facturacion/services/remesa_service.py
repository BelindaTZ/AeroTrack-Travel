"""RF-FAC-005 (CU-O36) — agrupar comisiones ya cobradas de una aerolínea/
periodo, sin remesa previa, en una remesa nueva."""

import datetime

from app.facturacion.repositories.facturacion_repo import FacturacionRepository


class SinComisionesParaRemesa(Exception):
    pass


async def generar_remesa(aerolinea_id: str, periodo: str) -> dict:
    repo = FacturacionRepository()
    comisiones = await repo.comisiones_cobradas_sin_remesa(aerolinea_id)
    if not comisiones:
        raise SinComisionesParaRemesa()

    monto_total = round(sum(c["monto"] for c in comisiones), 2)
    ahora_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")
    remesa = await repo.crear_remesa(
        {
            "aerolinea_id": aerolinea_id,
            "periodo": periodo,
            "monto_total": monto_total,
            "estado": "pendiente",
            "fecha_generacion": ahora_iso,
        }
    )
    for comision in comisiones:
        await repo.agregar_remesa_comision(remesa["id"], comision["id"])

    return remesa
