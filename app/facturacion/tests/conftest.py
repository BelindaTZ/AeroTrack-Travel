"""Fixtures propias de Facturación. `client`/`pb`/`usuario_factory`/
`vuelo_factory`/`tarifa_factory`/`pasajero_factory`/`reserva_factory`/
`admin_client`/`rol_administrador`/`rol_agente` vienen del conftest.py de
la raíz del repo."""

import pytest


@pytest.fixture
async def pago_factory(pb):
    """Crea un `pagos` desechable directamente (sin pasar por el servicio ni
    Stripe) — para pruebas que necesitan un pago exitoso ya existente."""
    creados: list[str] = []

    async def _crear(reserva_id: str, estado: str = "exitoso", monto: float = 199.0, **extra) -> dict:
        metodo = await pb.get_first("metodos_pago", "activo=true")
        data = {
            "reserva_id": reserva_id,
            "monto": monto,
            "moneda": "USD",
            "metodo_pago_id": metodo["id"],
            "estado": estado,
        }
        data.update(extra)
        pago = await pb.create_record("pagos", data)
        creados.append(pago["id"])
        return pago

    yield _crear

    for pago_id in creados:
        try:
            await pb.delete_record("pagos", pago_id)
        except Exception:
            pass
