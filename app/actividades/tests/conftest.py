"""Doble determinista de Travel Advisor — mismo criterio que
`app/hoteles/tests/conftest.py`/`app/autos/tests/conftest.py`."""

import pytest

from app.actividades.services.traveladvisor_client import TravelAdvisorClient


class TravelAdvisorClientFalso(TravelAdvisorClient):
    def __init__(
        self,
        geo_ids: dict[str, int | None] | None = None,
        tarjetas: dict[int, list[dict]] | None = None,
        detalles: dict[str, dict] | None = None,
    ):
        self.geo_ids = geo_ids or {}
        self.tarjetas = tarjetas or {}
        self.detalles = detalles or {}
        self.llamadas: list[str] = []

    async def resolver_geo_id(self, ciudad: str) -> int | None:
        self.llamadas.append(f"geo:{ciudad}")
        return self.geo_ids.get(ciudad)

    async def buscar_actividades(self, geo_id: int) -> list[dict]:
        self.llamadas.append(f"buscar:{geo_id}")
        return self.tarjetas.get(geo_id, [])

    async def obtener_detalle(self, content_id: str) -> dict:
        self.llamadas.append(f"detalle:{content_id}")
        return self.detalles.get(content_id, {})


@pytest.fixture
def traveladvisor_falso():
    return TravelAdvisorClientFalso


@pytest.fixture
async def actividad_factory(pb):
    """Crea actividades_catalogo desechables para pruebas de
    búsqueda/detalle/filtros (RF-ACT-001,002,003); las borra al finalizar."""
    creadas: list[str] = []

    async def _crear(
        ciudad: str = "Paris",
        pais: str = "France",
        nombre: str = "Paris Seine River Cruise",
        categoria: str = "Tours",
        precio_desde: float = 45.0,
        calificacion_promedio: float = 4.5,
        **extra,
    ) -> dict:
        data = {
            "nombre": nombre,
            "ciudad": ciudad,
            "pais": pais,
            "categoria": categoria,
            "calificacion_promedio": calificacion_promedio,
            "cantidad_resenas": 10,
            "descripcion": "Descripción de prueba.",
            "precio_desde": precio_desde,
            "moneda": "USD",
            "imagen_principal": "",
            "fuente_content_id": f"test-{ciudad}-{nombre}",
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        }
        data.update(extra)
        actividad = await pb.create_record("actividades_catalogo", data)
        creadas.append(actividad["id"])
        return actividad

    yield _crear

    for actividad_id in creadas:
        try:
            await pb.delete_record("actividades_catalogo", actividad_id)
        except Exception:
            pass


@pytest.fixture
async def horario_factory(pb):
    """Crea actividades_horarios desechables; los borra al finalizar."""
    creados: list[str] = []

    async def _crear(actividad_id: str, fecha: str = "2027-06-01", hora: str = "09:00", precio: float = 45.0, cupos_disponibles: int = 15) -> dict:
        horario = await pb.create_record(
            "actividades_horarios",
            {
                "actividad_id": actividad_id, "fecha": fecha, "hora": hora,
                "cupos_disponibles": cupos_disponibles, "precio": precio, "moneda": "USD",
                "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
            },
        )
        creados.append(horario["id"])
        return horario

    yield _crear

    for horario_id in creados:
        try:
            await pb.delete_record("actividades_horarios", horario_id)
        except Exception:
            pass


@pytest.fixture
async def resena_factory(pb):
    """Crea actividades_resenas desechables; las borra al finalizar."""
    creadas: list[str] = []

    async def _crear(actividad_id: str, autor: str = "Viajero Test", calificacion: float = 5, comentario: str = "Excelente") -> dict:
        resena = await pb.create_record(
            "actividades_resenas",
            {
                "actividad_id": actividad_id, "autor": autor, "calificacion": calificacion,
                "comentario": comentario, "fecha_resena": "2027-01-01 00:00:00.000Z",
                "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
            },
        )
        creadas.append(resena["id"])
        return resena

    yield _crear

    for resena_id in creadas:
        try:
            await pb.delete_record("actividades_resenas", resena_id)
        except Exception:
            pass
