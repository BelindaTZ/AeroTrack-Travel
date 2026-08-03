"""DB-10 — Efectividad de Campañas y Promociones (100% MinIO operacional,
sin tabla ClickHouse — spec así lo define).

Reutiliza `reporte_cupones()` del propio módulo Ofertas en vez de
reimplementar el cruce cupón/uso. Dos gaps de datos reales documentados:
- No existe tracking de apertura de email en ningún lado del proyecto
  (`campanas_email` no tiene campo de aperturas/clics) — se muestra "sin
  datos" en vez de inventar un %.
- `newsletter_suscripciones` no tiene fecha de baja — se usa `updated` de
  los registros con `activo=false` como proxy de cuándo se dieron de baja.
"""

from __future__ import annotations

import datetime

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.ofertas.repositories.ofertas_repo import OfertasRepository
from app.ofertas.services.ofertas_service import reporte_cupones


async def obtener_datos_campanas(desde: datetime.date, hasta: datetime.date) -> dict:
    reporte = await reporte_cupones(desde.isoformat())
    cupones_canjeados = sum(c["usos"] for c in reporte)
    cupones_emitidos = len(reporte)
    descuento_total = round(sum(c["monto_total"] for c in reporte), 2)

    por_tipo: dict[str, dict] = {}
    for c in reporte:
        acc = por_tipo.setdefault(c["tipo"], {"usos": 0, "monto": 0.0})
        acc["usos"] += c["usos"]
        acc["monto"] += c["monto_total"]
    cupones_por_tipo = [{"tipo": k, "usos": v["usos"], "monto": round(v["monto"], 2)} for k, v in por_tipo.items()]

    ultima_campana = (await OfertasRepository().listar_campanas())
    ultima_campana = ultima_campana[0] if ultima_campana else None

    suscriptores = await OfertasRepository().listar_todos_suscriptores()
    altas_semana: dict[str, int] = {}
    bajas_semana: dict[str, int] = {}
    for s in suscriptores:
        fecha_alta = s.get("fecha_suscripcion")
        if fecha_alta:
            f = datetime.datetime.fromisoformat(fecha_alta.replace("Z", "+00:00")).date()
            if desde <= f <= hasta:
                semana = (f - datetime.timedelta(days=f.weekday())).isoformat()
                altas_semana[semana] = altas_semana.get(semana, 0) + 1
        if not s.get("activo") and s.get("updated"):
            f = datetime.datetime.fromisoformat(s["updated"].replace("Z", "+00:00")).date()
            if desde <= f <= hasta:
                semana = (f - datetime.timedelta(days=f.weekday())).isoformat()
                bajas_semana[semana] = bajas_semana.get(semana, 0) + 1

    semanas = sorted(set(altas_semana) | set(bajas_semana))

    favoritos = await CuentaRepository().listar_todos_favoritos()
    favoritos_periodo = [
        f for f in favoritos if f.get("fecha_guardado") and desde.isoformat() <= f["fecha_guardado"][:10] <= hasta.isoformat()
    ]
    conteo_destino: dict[str, int] = {}
    conteo_tipo: dict[str, int] = {}
    for f in favoritos_periodo:
        tipo = f.get("tipo") or "sin_tipo"
        conteo_tipo[tipo] = conteo_tipo.get(tipo, 0) + 1
        clave = f.get("producto_ref") or "—"
        conteo_destino[clave] = conteo_destino.get(clave, 0) + 1
    top_favoritos = sorted(
        [{"referencia": k, "veces_guardado": v} for k, v in conteo_destino.items()], key=lambda x: x["veces_guardado"], reverse=True
    )[:10]

    return {
        "cupones_canjeados": cupones_canjeados,
        "cupones_emitidos": cupones_emitidos,
        "pct_sobre_emitidos": round(cupones_canjeados / cupones_emitidos * 100, 2) if cupones_emitidos else 0.0,
        "descuento_total": descuento_total,
        "ultima_campana_nombre": ultima_campana["nombre"] if ultima_campana else None,
        "ultima_campana_apertura": None,  # sin tracking real — ver docstring
        "cupones_por_tipo": cupones_por_tipo,
        "suscriptores_semana": {"semanas": semanas, "altas": [altas_semana.get(s, 0) for s in semanas], "bajas": [bajas_semana.get(s, 0) for s in semanas]},
        "top_favoritos": top_favoritos,
        "favoritos_por_tipo": [{"tipo": k, "total": v} for k, v in conteo_tipo.items()],
    }
