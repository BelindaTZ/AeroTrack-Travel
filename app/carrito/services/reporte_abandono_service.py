"""RF-CAR-T02 (CU-T27) — reporte de carritos abandonados y tasa de
recuperación por período.

`carritos.fue_abandonado` es la única fuente de verdad de si un carrito
pasó por abandono alguna vez: un carrito puede volver a `activo`
(`CarritoRepository.carrito_de_trabajo`, recuperación en curso) y luego a
`convertido`, y en ese punto su `estado` final ya no dice que pasó por
abandono — reconstruir eso del `estado` actual perdería exactamente el
caso que RN-CAR-T02 pide contar como recuperado.

RN-CAR-T02: un carrito que se convierte SIN haber pasado nunca por
`abandonado` no participa en la tasa (`fue_abandonado=false` lo excluye
del filtro base)."""

import datetime

from app.carrito.repositories.carrito_repo import CarritoRepository

DIAS_DEFAULT = 30


async def reporte_recuperacion(dias: int = DIAS_DEFAULT) -> dict:
    repo = CarritoRepository()
    desde_iso = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=dias)
    ).strftime("%Y-%m-%d %H:%M:%S.000Z")

    carritos = await repo.carritos_abandonados_desde(desde_iso)
    total = len(carritos)
    recuperados = sum(1 for c in carritos if c["estado"] == "convertido")
    tasa = round(recuperados / total * 100, 1) if total else 0.0

    return {"total_abandonados": total, "recuperados": recuperados, "tasa_recuperacion": tasa}
