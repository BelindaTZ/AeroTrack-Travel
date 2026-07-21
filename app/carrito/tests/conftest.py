# Fixtures compartidas (client, pb, pasajero_factory, pasajero_client, ...)
# viven en el conftest.py de la raíz del repo — pytest las descubre
# automáticamente, no requieren import aquí.

import pytest


@pytest.fixture
async def auto_factory(pb):
    """Mismo fixture que `app/autos/tests/conftest.py` — duplicado aquí
    porque las fixtures de un módulo no son visibles para los tests de
    otro; Carrito necesita un auto real para probar la vista de
    agregar/eliminar/checkout (RF-CAR-001..004) sobre un producto real."""
    creados: list[str] = []

    async def _crear(ciudad_recogida: str = "Paris", precio_dia: float = 63.0, **extra) -> dict:
        data = {
            "proveedor_agregador": "expedia",
            "marca": "",
            "modelo": "Opel Mokka",
            "categoria": "SUV",
            "transmision": "Automatic",
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


@pytest.fixture
async def actividad_con_horario_factory(pb):
    """Crea una actividad + un horario real (con cupo explícito) para
    probar la reserva/liberación de cupo de Carrito sobre Actividades."""
    actividades: list[str] = []
    horarios: list[str] = []

    async def _crear(cupos_disponibles: int = 3, precio: float = 45.0) -> tuple[dict, dict]:
        actividad = await pb.create_record(
            "actividades_catalogo",
            {
                "nombre": "Actividad de Prueba Carrito", "ciudad": "Paris", "pais": "France",
                "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
            },
        )
        actividades.append(actividad["id"])
        horario = await pb.create_record(
            "actividades_horarios",
            {
                "actividad_id": actividad["id"], "fecha": "2027-06-01", "hora": "09:00",
                "cupos_disponibles": cupos_disponibles, "precio": precio, "moneda": "USD",
                "fecha_actualizacion": "2027-01-01 00:00:00.000Z",
            },
        )
        horarios.append(horario["id"])
        return actividad, horario

    yield _crear

    for horario_id in horarios:
        try:
            await pb.delete_record("actividades_horarios", horario_id)
        except Exception:
            pass
    for actividad_id in actividades:
        try:
            await pb.delete_record("actividades_catalogo", actividad_id)
        except Exception:
            pass
