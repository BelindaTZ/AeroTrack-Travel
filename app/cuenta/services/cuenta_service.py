"""RF-CTA-001 — agrupa las reservas de un pasajero en próxima/activa/pasada
según la fecha real del producto (vuelo/actividad/crucero), reutilizando
`construir_detalle` de Reservas para no duplicar la resolución de cada
reserva. Hotel/Auto no aportan fecha todavía (ver `fecha_referencia_item`,
`errores-conocidos.md`) — una reserva sin ningún ítem con fecha resoluble
cae en el grupo `sin_fecha`, nunca se le inventa una fecha."""

from datetime import date, datetime, timedelta, timezone

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.cuenta.schemas import MovimientoPuntosOut, PuntosResumenOut
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.reservas.router_reservas import construir_detalle
from app.shared.descripcion_producto import fecha_referencia_item


async def mis_viajes_agrupados(pasajero_id: str) -> dict[str, list]:
    repo = ReservasRepository()
    reservas = await repo.listar_reservas_de_pasajero(pasajero_id)

    hoy = date.today()
    con_fecha: list[tuple[date, object]] = []
    sin_fecha: list = []

    for r in reservas:
        detalle = await construir_detalle(r)
        items = await repo.items_de_reserva(r["id"])
        rangos = [rango for item in items if (rango := await fecha_referencia_item(item)) is not None]
        if not rangos:
            sin_fecha.append(detalle)
            continue
        inicio = min(date.fromisoformat(rango[0]) for rango in rangos)
        fin = max(date.fromisoformat(rango[1]) for rango in rangos)
        con_fecha.append((inicio, fin, detalle))

    proximas = sorted((t for t in con_fecha if hoy < t[0]), key=lambda t: t[0])
    activas = sorted((t for t in con_fecha if t[0] <= hoy <= t[1]), key=lambda t: t[0])
    pasadas = sorted((t for t in con_fecha if hoy > t[1]), key=lambda t: t[0], reverse=True)

    return {
        "proximas": [t[2] for t in proximas],
        "activas": [t[2] for t in activas],
        "pasadas": [t[2] for t in pasadas],
        "sin_fecha": sin_fecha,
    }


def _parse_fecha_pb(valor: str) -> datetime:
    return datetime.strptime(valor[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


async def resumen_puntos(pasajero_id: str) -> PuntosResumenOut:
    """RF-CTA-006/RN-CTA-002 — el nivel vigente se deriva del saldo BRUTO
    (todos los movimientos, sin filtrar por vencimiento — un nivel se gana
    por actividad histórica, no se pierde solo porque puntos viejos
    caduquen); una vez conocido el nivel, su `vencimiento_meses` decide qué
    acumulaciones siguen contando para el saldo VIGENTE (el que se muestra).
    Las redenciones (gasto de puntos) nunca vencen — restan siempre."""
    repo = CuentaRepository()
    movimientos = await repo.movimientos_de_pasajero(pasajero_id)
    niveles = await repo.niveles_programa_beneficios()  # ascendente por puntos_minimos

    saldo_bruto = sum(
        m["puntos"] if m["tipo"] == "acumulacion" else -m["puntos"] for m in movimientos
    )

    nivel_actual: str | None = None
    vencimiento_meses: float | None = None
    for nivel in niveles:
        if saldo_bruto >= (nivel.get("puntos_minimos") or 0):
            nivel_actual = nivel["nombre_nivel"]
            vencimiento_meses = nivel.get("vencimiento_meses")

    ahora = datetime.now(timezone.utc)
    limite = ahora - timedelta(days=30 * vencimiento_meses) if vencimiento_meses else None

    saldo_vigente = 0.0
    movimientos_out: list[MovimientoPuntosOut] = []
    for m in movimientos:
        if m["tipo"] == "acumulacion":
            vigente = limite is None or _parse_fecha_pb(m["fecha"]) >= limite
            if vigente:
                saldo_vigente += m["puntos"]
        else:  # redencion — siempre cuenta, nunca vence
            vigente = True
            saldo_vigente -= m["puntos"]
        movimientos_out.append(
            MovimientoPuntosOut(
                tipo=m["tipo"], puntos=m["puntos"], fecha=m["fecha"],
                descripcion=m.get("descripcion") or None, reserva_id=m.get("reserva_id") or None,
                vigente=vigente,
            )
        )

    return PuntosResumenOut(saldo_vigente=saldo_vigente, nivel_actual=nivel_actual, movimientos=movimientos_out)
