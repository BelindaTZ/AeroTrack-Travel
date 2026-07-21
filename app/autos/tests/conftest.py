"""Doble determinista de Global Rental Cars — mismo criterio que
`app/hoteles/tests/conftest.py`: la integración real ya se probó en vivo
esta sesión, pero la suite automatizada no debe depender de la API real
en cada corrida."""

import pytest

from app.autos.services.rentalcars_client import RentalCarsClient


@pytest.fixture
async def auto_factory(pb):
    """Crea autos_catalogo desechables para pruebas de búsqueda/detalle
    (RF-AUT-001,002,003); los borra al finalizar."""
    creados: list[str] = []

    async def _crear(
        ciudad_recogida: str = "Paris",
        categoria: str = "SUV",
        modelo: str = "Opel Mokka",
        transmision: str | None = "Automatic",
        precio_dia: float = 63.0,
        proveedor_agregador: str = "expedia",
        **extra,
    ) -> dict:
        data = {
            "proveedor_agregador": proveedor_agregador,
            "marca": "",
            "modelo": modelo,
            "categoria": categoria,
            "transmision": transmision,
            "ciudad_recogida": ciudad_recogida,
            "aeropuerto_codigo": "CDG",
            "precio_dia": precio_dia,
            "moneda": "USD",
            "modalidad_pago_disponible": "pagar_al_recoger",
            "fuente_oferta_ref": "token-test",
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        }
        data.update(extra)
        auto = await pb.create_record("autos_catalogo", data)
        creados.append(auto["id"])
        return auto

    yield _crear

    for auto_id in creados:
        try:
            await pb.delete_record("autos_catalogo", auto_id)
        except Exception:
            pass


class RentalCarsClientFalso(RentalCarsClient):
    def __init__(
        self,
        codigos: dict[str, str | None] | None = None,
        tarjetas: dict[str, list[dict]] | None = None,
    ):
        self.codigos = codigos or {}
        self.tarjetas = tarjetas or {}
        self.llamadas: list[str] = []

    async def resolver_codigo_ciudad(self, ciudad: str) -> str | None:
        self.llamadas.append(f"resolver:{ciudad}")
        return self.codigos.get(ciudad)

    async def buscar_autos(self, codigo_ciudad: str) -> list[dict]:
        self.llamadas.append(f"buscar:{codigo_ciudad}")
        return self.tarjetas.get(codigo_ciudad, [])


@pytest.fixture
def rentalcars_falso():
    return RentalCarsClientFalso
