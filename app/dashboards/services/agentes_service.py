"""DB-13 — Productividad del Agente.

Vista global (admin_operaciones) o filtrada por agente (rol Agente, ve
solo lo propio) — a diferencia del resto de los dashboards, este SÍ
necesita saber quién pregunta, no solo qué rol tiene. `reservas.agente_id`
y `casos_escalados.agente_asignado_id` son las únicas señales reales de
"quién atendió qué" en todo el esquema — no existe una colección
`tickets_soporte` separada (spec la menciona, mapea 1:1 a `casos_escalados`,
mismo criterio que "vuelos_monitoreo" -> `vuelos_catalogo` en DB-03).
"""

from __future__ import annotations

import datetime

from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared.pocketbase_client import get_pocketbase_client


async def obtener_datos_agentes(desde: datetime.date, hasta: datetime.date, agente_id: str | None = None) -> dict:
    reservas = await ReservasRepository().listar_todas()
    reservas_asistidas = [
        r for r in reservas
        if r.get("agente_id") and r.get("fecha_reserva") and desde.isoformat() <= r["fecha_reserva"][:10] <= hasta.isoformat()
    ]
    if agente_id:
        reservas_asistidas = [r for r in reservas_asistidas if r["agente_id"] == agente_id]

    casos = await CentroAyudaRepository().listar_casos()
    casos_periodo = [
        c for c in casos if c.get("fecha_creacion") and desde.isoformat() <= c["fecha_creacion"][:10] <= hasta.isoformat()
    ]
    if agente_id:
        casos_periodo = [c for c in casos_periodo if c.get("agente_asignado_id") == agente_id]

    resueltos = sum(1 for c in casos_periodo if c.get("estado") == "resuelto")
    pendientes = sum(1 for c in casos_periodo if c.get("estado") != "resuelto")

    pb = get_pocketbase_client()

    por_agente: dict[str, dict] = {}
    for r in reservas_asistidas:
        acc = por_agente.setdefault(r["agente_id"], {"reservas": 0, "valor": 0.0, "casos_resueltos": 0})
        acc["reservas"] += 1
        acc["valor"] += r.get("total_pagar") or 0
    for c in casos_periodo:
        aid = c.get("agente_asignado_id")
        if aid and c.get("estado") == "resuelto":
            por_agente.setdefault(aid, {"reservas": 0, "valor": 0.0, "casos_resueltos": 0})["casos_resueltos"] += 1

    ranking = []
    for aid, datos in por_agente.items():
        try:
            usuario_agente = await pb.get_record("usuarios", aid)
            nombre = usuario_agente.get("nombre_completo", aid)
        except Exception:
            nombre = aid
        ranking.append({"agente_id": aid, "nombre": nombre, **datos, "valor": round(datos["valor"], 2)})
    ranking.sort(key=lambda x: x["reservas"], reverse=True)

    agente_top = ranking[0]["nombre"] if ranking else None

    hoy = datetime.date.today()
    inicio_8_semanas = hoy - datetime.timedelta(weeks=8)
    top3_ids = [r["agente_id"] for r in ranking[:3]]
    semana_agente_conteo: dict[tuple[str, str], int] = {}
    for r in reservas:
        if r.get("agente_id") not in top3_ids or not r.get("fecha_reserva"):
            continue
        fecha = datetime.datetime.fromisoformat(r["fecha_reserva"].replace("Z", "+00:00")).date()
        if fecha < inicio_8_semanas:
            continue
        semana = (fecha - datetime.timedelta(days=fecha.weekday())).isoformat()
        clave = (semana, r["agente_id"])
        semana_agente_conteo[clave] = semana_agente_conteo.get(clave, 0) + 1
    semanas = sorted({k[0] for k in semana_agente_conteo})
    productividad_top3 = {
        next((r["nombre"] for r in ranking if r["agente_id"] == aid), aid): [semana_agente_conteo.get((s, aid), 0) for s in semanas]
        for aid in top3_ids
    }

    return {
        "total_reservas_asistidas": len(reservas_asistidas),
        "valor_total_gestionado": round(sum(r.get("total_pagar") or 0 for r in reservas_asistidas), 2),
        "agente_top": agente_top,
        "casos_resueltos": resueltos,
        "casos_pendientes": pendientes,
        "ranking_agentes": ranking,
        "semanas": semanas,
        "productividad_top3": productividad_top3,
        "vista_propia": agente_id is not None,
    }
