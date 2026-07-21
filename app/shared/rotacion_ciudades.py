"""Rebanada rotativa determinística de una lista curada de ciudades —
usada por catálogos periódicos (Hoteles/Actividades) para que cada corrida
solo toque un subconjunto y no todo el universo curado a la vez (respeta
rate limits/prudencia con proveedores sin cuota mensual documentada), sin
necesitar estado propio en BD: se deriva del día del año, así que es
reproducible y fácil de auditar (misma rebanada si se corre dos veces el
mismo día)."""

import datetime


def rebanada_rotativa(items: list[str], tamano: int, hoy: datetime.date | None = None) -> list[str]:
    if not items or tamano >= len(items):
        return items
    hoy = hoy or datetime.date.today()
    indice = hoy.timetuple().tm_yday
    inicio = (indice * tamano) % len(items)
    return (items * 2)[inicio : inicio + tamano]
