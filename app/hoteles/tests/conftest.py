"""Doble determinista de HotelLens — mismo criterio que
`app/disrupciones/tests/conftest.py`: la integración real ya se probó una
vez contra la API real (ver `errores-conocidos.md` / evidencia manual de
esta sesión), pero la suite automatizada no debe gastar la cuota real
(rate limit estricto, ~4-5 llamadas/min) en cada corrida."""

import pytest

from app.hoteles.services.hotellens_client import HotelLensClient
from app.shared import minio_catalog_reader


class HotelLensClientFalso(HotelLensClient):
    def __init__(
        self,
        resultados_busqueda: dict[str, list[dict]] | None = None,
        ofertas: dict[str, list[dict]] | None = None,
        detalles: dict[str, dict] | None = None,
        resenas: dict[str, list[dict]] | None = None,
    ):
        self.resultados_busqueda = resultados_busqueda or {}
        self.ofertas = ofertas or {}
        self.detalles = detalles or {}
        self.resenas = resenas or {}
        self.llamadas: list[str] = []

    async def buscar_hoteles(self, ciudad: str) -> list[dict]:
        self.llamadas.append(f"buscar:{ciudad}")
        return self.resultados_busqueda.get(ciudad, [])

    async def obtener_ofertas(self, url_entidad: str) -> list[dict]:
        self.llamadas.append(f"ofertas:{url_entidad}")
        return self.ofertas.get(url_entidad, [])

    async def obtener_detalle_booking(self, hotel_id_booking: str, check_in: str, check_out: str) -> dict:
        self.llamadas.append(f"detalle:{hotel_id_booking}")
        return self.detalles.get(hotel_id_booking, {})

    async def obtener_resenas(self, url_entidad: str) -> list[dict]:
        self.llamadas.append(f"resenas:{url_entidad}")
        return self.resenas.get(url_entidad, [])


@pytest.fixture
def hotellens_falso():
    return HotelLensClientFalso


@pytest.fixture
async def hotel_factory(pb):
    """Crea hoteles_catalogo desechables para pruebas de búsqueda/detalle/
    filtros (RF-HOT-001,002,003); los borra al finalizar."""
    creados: list[str] = []

    async def _crear(
        ciudad: str = "Paris", pais: str = "France", nombre: str = "Hilton Paris Opera",
        estrellas: float = 4, calificacion_promedio: float = 4.5, **extra,
    ) -> dict:
        data = {
            "nombre": nombre, "direccion": "1 Rue de Test", "ciudad": ciudad, "pais": pais,
            "estrellas": estrellas, "calificacion_promedio": calificacion_promedio, "cantidad_resenas": 20,
            "descripcion_corta": "", "descripcion": "Descripción de prueba.",
            "servicios": ["WiFi gratis", "Piscina"], "hora_checkin": "15:00", "hora_checkout": "11:00",
            "imagen_principal": "", "fuente_entity_url": f"test-{ciudad}-{nombre}",
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        }
        data.update(extra)
        hotel = await pb.create_record("hoteles_catalogo", data)
        creados.append(hotel["id"])
        await minio_catalog_reader.publicar_y_refrescar("hoteles_catalogo")
        return hotel

    yield _crear

    for hotel_id in creados:
        try:
            await pb.delete_record("hoteles_catalogo", hotel_id)
        except Exception:
            pass
    if creados:
        await minio_catalog_reader.publicar_y_refrescar("hoteles_catalogo")


@pytest.fixture
async def tarifa_hotel_factory(pb):
    creadas: list[str] = []

    async def _crear(
        hotel_id: str, tipo_habitacion: str = "Standard Room", precio_final: float = 120.0,
        reembolsable: bool = True, cupos_disponibles: int = 3, **extra,
    ) -> dict:
        data = {
            "hotel_id": hotel_id, "tipo_habitacion": tipo_habitacion, "bed_type": "1 King Bed",
            "max_ocupantes": 2, "desayuno_incluido": False, "precio_final": precio_final, "moneda": "USD",
            "reembolsable": reembolsable, "cupos_disponibles": cupos_disponibles,
            "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        }
        data.update(extra)
        tarifa = await pb.create_record("hoteles_tarifas", data)
        creadas.append(tarifa["id"])
        await minio_catalog_reader.publicar_y_refrescar("hoteles_tarifas")
        return tarifa

    yield _crear

    for tarifa_id in creadas:
        try:
            await pb.delete_record("hoteles_tarifas", tarifa_id)
        except Exception:
            pass
    if creadas:
        await minio_catalog_reader.publicar_y_refrescar("hoteles_tarifas")


@pytest.fixture
async def disponibilidad_hotel_factory(pb):
    """Crea filas de `hoteles_disponibilidad` (una noche) desechables para
    pruebas de RF-HOT-004 (disponibilidad real por fecha); las borra al
    finalizar."""
    creadas: list[str] = []

    async def _crear(hotel_id: str, hotel_tarifa_id: str, fecha: str, cupos_disponibles: int = 3, **extra) -> dict:
        data = {
            "hotel_id": hotel_id, "hotel_tarifa_id": hotel_tarifa_id, "fecha": fecha,
            "cupos_disponibles": cupos_disponibles, "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
        }
        data.update(extra)
        fila = await pb.create_record("hoteles_disponibilidad", data)
        creadas.append(fila["id"])
        await minio_catalog_reader.publicar_y_refrescar("hoteles_disponibilidad")
        return fila

    yield _crear

    for fila_id in creadas:
        try:
            await pb.delete_record("hoteles_disponibilidad", fila_id)
        except Exception:
            pass
    if creadas:
        await minio_catalog_reader.publicar_y_refrescar("hoteles_disponibilidad")


@pytest.fixture
async def resena_hotel_factory(pb):
    creadas: list[str] = []

    async def _crear(hotel_id: str, autor: str = "Huésped Test", calificacion: float = 9.0, comentario: str = "Excelente") -> dict:
        resena = await pb.create_record(
            "hoteles_resenas",
            {
                "hotel_id": hotel_id, "autor": autor, "calificacion": calificacion, "escala_calificacion": 10,
                "comentario": comentario, "fecha_relativa_texto": "hace 2 meses", "fuente": "Booking.com",
                "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
            },
        )
        creadas.append(resena["id"])
        await minio_catalog_reader.publicar_y_refrescar("hoteles_resenas")
        return resena

    yield _crear

    for resena_id in creadas:
        try:
            await pb.delete_record("hoteles_resenas", resena_id)
        except Exception:
            pass
    if creadas:
        await minio_catalog_reader.publicar_y_refrescar("hoteles_resenas")
