"""Doble determinista de Cruise Pricing API — mismo criterio que los
demás módulos de catálogo nuevos esta sesión."""

import pytest

from app.cruceros.services.cruisepricing_client import CruisePricingClient


class CruisePricingClientFalso(CruisePricingClient):
    def __init__(
        self,
        navieras: list[dict] | None = None,
        cruceros: list[dict] | None = None,
        detalles: dict[str, dict] | None = None,
    ):
        self.navieras = navieras or []
        self.cruceros = cruceros or []
        self.detalles = detalles or {}
        self.llamadas: list[str] = []

    async def listar_navieras(self) -> list[dict]:
        self.llamadas.append("navieras")
        return self.navieras

    async def buscar_cruceros(self, limite: int) -> list[dict]:
        self.llamadas.append(f"buscar:{limite}")
        return self.cruceros[:limite]

    async def obtener_detalle(self, cruise_id: str) -> dict:
        self.llamadas.append(f"detalle:{cruise_id}")
        return self.detalles.get(cruise_id, {})


@pytest.fixture
def cruisepricing_falso():
    return CruisePricingClientFalso


@pytest.fixture
async def naviera_factory(pb):
    creadas: list[str] = []

    async def _crear(nombre: str = "Carnival", slug_proveedor: str | None = None) -> dict:
        naviera = await pb.create_record(
            "navieras",
            {
                "nombre": nombre, "slug_proveedor": slug_proveedor or f"{nombre.lower()}-{len(creadas)}",
                "destinos": ["Caribbean"], "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
            },
        )
        creadas.append(naviera["id"])
        return naviera

    yield _crear

    for naviera_id in creadas:
        try:
            await pb.delete_record("navieras", naviera_id)
        except Exception:
            pass


@pytest.fixture
async def barco_factory(pb):
    creados: list[str] = []

    async def _crear(naviera_id: str, nombre: str = "Carnival Valor") -> dict:
        barco = await pb.create_record(
            "barcos", {"naviera_id": naviera_id, "nombre": nombre, "fecha_actualizacion": "2027-01-01 00:00:00.000Z"}
        )
        creados.append(barco["id"])
        return barco

    yield _crear

    for barco_id in creados:
        try:
            await pb.delete_record("barcos", barco_id)
        except Exception:
            pass


@pytest.fixture
async def crucero_factory(pb):
    creados: list[str] = []

    async def _crear(
        naviera_id: str, barco_id: str, fecha_zarpe: str = "2027-06-01",
        duracion_dias: float = 7, precio_base: float = 700.0,
        itinerario_puertos: list | None = None, **extra,
    ) -> dict:
        # Forma real confirmada en vivo (Cruise Pricing API): lista de
        # {"day": N, "port": "..."}, no strings planos — ver
        # errores-conocidos.md, "Módulo Cruceros — Fase 3".
        puertos_default = [{"day": 1, "port": "Miami, FL"}, {"day": 2, "port": "Nassau, Bahamas"}]
        data = {
            "naviera_id": naviera_id, "barco_id": barco_id,
            "fuente_cruise_id": f"test-{len(creados)}", "fecha_zarpe": fecha_zarpe,
            "duracion_dias": duracion_dias, "itinerario_puertos": itinerario_puertos or puertos_default,
            "precio_base": precio_base, "moneda": "USD", "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        }
        data.update(extra)
        crucero = await pb.create_record("cruceros_catalogo", data)
        creados.append(crucero["id"])
        return crucero

    yield _crear

    for crucero_id in creados:
        try:
            await pb.delete_record("cruceros_catalogo", crucero_id)
        except Exception:
            pass


@pytest.fixture
async def camarote_factory(pb):
    creados: list[str] = []

    async def _crear(crucero_id: str, tipo_camarote: str = "INTERIOR", precio_por_persona: float = 700.0, cupos_disponibles: int = 20) -> dict:
        camarote = await pb.create_record(
            "cruceros_camarotes_tarifa",
            {
                "crucero_id": crucero_id, "tipo_camarote": tipo_camarote,
                "precio_por_persona": precio_por_persona, "cupos_disponibles": cupos_disponibles,
                "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
            },
        )
        creados.append(camarote["id"])
        return camarote

    yield _crear

    for camarote_id in creados:
        try:
            await pb.delete_record("cruceros_camarotes_tarifa", camarote_id)
        except Exception:
            pass
