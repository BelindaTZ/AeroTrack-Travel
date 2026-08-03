"""WP-16 (auditoría de WorkPanels, 2026-08-01) — ajuste manual puntual de
`tarifas_vuelo.precio_final`/`cupos_disponibles`. Mismo patrón que
`forzar_estado_service.py` (motivo obligatorio + auditoría): las tarifas
se generan y actualizan automáticamente por `enriquecimiento_service.py`
(AeroDataBox/Google Flights), así que este es el único punto de escritura
pensado para un actor humano, marcado siempre como excepción trazable."""

from app.seguridad.services.audit_service import AuditService
from app.vuelos.repositories.vuelos_repo import VuelosRepository


class MotivoRequerido(Exception):
    pass


class TarifaInvalida(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def ajustar_tarifa_manual(
    usuario: dict, tarifa_id: str, precio_final: float, cupos_disponibles: int | None, motivo: str
) -> dict:
    if not motivo.strip():
        raise MotivoRequerido()

    repo = VuelosRepository()
    tarifa = await repo.obtener_tarifa(tarifa_id)
    if tarifa is None:
        raise TarifaInvalida("Tarifa no encontrada")

    data: dict = {"precio_final": precio_final}
    if cupos_disponibles is not None:
        data["cupos_disponibles"] = cupos_disponibles

    actualizada = await repo.actualizar_tarifa(tarifa_id, data)
    await AuditService().insertar(
        "ajustar_tarifa_manual", "tarifas_vuelo", usuario_id=usuario["id"], registro_id=tarifa_id,
        detalle={"motivo": motivo, "precio_final": precio_final, "cupos_disponibles": cupos_disponibles},
    )
    return actualizada
