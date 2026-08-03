"""RF-FAC-005 (CU-O36) — agrupar comisiones ya cobradas de una aerolínea/
periodo, sin remesa previa, en una remesa nueva."""

import datetime

from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.seguridad.services.audit_service import AuditService


class SinComisionesParaRemesa(Exception):
    pass


class RemesaInvalida(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


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


async def marcar_remesa_pagada(usuario: dict, remesa_id: str) -> dict:
    """WP-14 (auditoría de WorkPanels, 2026-07-31) — antes no existía
    ningún camino de código que escribiera esta transición."""
    repo = FacturacionRepository()
    remesa = await repo.obtener_remesa(remesa_id)
    if remesa is None:
        raise RemesaInvalida("Remesa no encontrada")
    if remesa.get("estado") == "pagada":
        raise RemesaInvalida("Esa remesa ya estaba pagada")

    actualizada = await repo.actualizar_remesa(remesa_id, {"estado": "pagada"})
    await AuditService().insertar(
        "marcar_remesa_pagada", "remesas", usuario_id=usuario["id"], registro_id=remesa_id
    )
    return actualizada
