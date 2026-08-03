"""Fechas de un rango semi-abierto `[fecha_inicio, fecha_fin)` — una
estadía de hotel o renta de auto consume cada NOCHE/DÍA en ese rango,
nunca la fecha de checkout/devolución en sí (ej. checkin=08-01,
checkout=08-03 consume 08-01 y 08-02, dos noches). Un solo lugar para la
convención, compartido por el lado de lectura (`disponibilidad_service.py`
de Hoteles/Autos, cupo mínimo del rango) y el de escritura
(`cupo_rango_service.py`, reserva/liberación por fila)."""

import datetime


def fechas_rango(fecha_inicio: str, fecha_fin: str) -> list[str]:
    d0 = datetime.date.fromisoformat(fecha_inicio[:10])
    d1 = datetime.date.fromisoformat(fecha_fin[:10])
    return [(d0 + datetime.timedelta(days=i)).isoformat() for i in range((d1 - d0).days)]
