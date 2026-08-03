"""CU-T11 — reporte de reservas de autos por proveedor/categoría."""

import datetime

from app.autos.repositories.autos_repo import AutosRepository

DIAS_DEFAULT = 90


async def reporte_por_proveedor_categoria(
    dias: int = DIAS_DEFAULT, ahora: datetime.datetime | None = None
) -> list[dict]:
    repo = AutosRepository()
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    desde = (ahora - datetime.timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S.000Z")
    items = await repo.items_de_auto_desde(desde)

    autos_cache: dict[str, dict | None] = {}
    agrupado: dict[tuple[str, str], dict] = {}
    for item in items:
        auto_id = item.get("auto_id")
        if not auto_id:
            continue
        if auto_id not in autos_cache:
            autos_cache[auto_id] = await repo.obtener_auto(auto_id)
        auto = autos_cache[auto_id]
        if auto is None:
            continue  # oferta point-in-time ya reemplazada (RN-AUT-001) — no rompe el reporte

        clave = (auto.get("proveedor_agregador") or "—", auto.get("categoria") or "—")
        if clave not in agrupado:
            agrupado[clave] = {
                "proveedor": clave[0], "categoria": clave[1],
                "reservas": 0, "confirmadas": 0, "ingresos": 0.0,
            }
        fila = agrupado[clave]
        fila["reservas"] += 1
        if item.get("estado_item") in ("confirmado", "completado"):
            fila["confirmadas"] += 1
        fila["ingresos"] += item.get("precio_final") or 0.0

    filas = list(agrupado.values())
    filas.sort(key=lambda f: f["reservas"], reverse=True)
    return filas
