"""DB-11 — Inteligencia del Asistente IA (100% MinIO operacional, sin
tabla ClickHouse — spec así lo define).

Gaps de esquema real, no de código — `mensajes_ia` no tiene ningún campo
de tema/tag, calificación positiva/negativa, ni tipo informativa/
transaccional (confirmado contra el dbml v3, mismo criterio que otros
gaps documentados en esta sesión):
- "Temas más consultados" muestra el texto literal de cada consulta
  (deduplicado y contado) — no hay clustering de temas real posible sin
  inventar una taxonomía.
- "% con calificación positiva" se reemplaza por "% con respuesta
  verificable" (inverso de "sin respuesta"), reutilizando la única señal
  real que ya existe en el módulo (`reporte_consultas()`, RF-IA-T02): los
  mensajes de fallback canónico son la única forma de detectar una
  respuesta no satisfactoria sin un campo de estado propio.
- "Consultas por tipo (informativas vs transaccionales)" se omite del
  todo — no existe ninguna señal real para clasificar sin inventar
  keywords, y esta sesión evita fabricar categorías sin respaldo de dato.
"""

from __future__ import annotations

import datetime

from app.asistente_ia.repositories.asistente_repo import AsistenteRepository
from app.asistente_ia.services.asistente_service import _MARCADORES_SIN_RESPUESTA


async def obtener_datos_asistente_ia(desde: datetime.date, hasta: datetime.date) -> dict:
    repo = AsistenteRepository()
    mensajes = await repo.mensajes_de_pasajero_en_periodo(desde.isoformat())
    mensajes_periodo = [m for m in mensajes if m.get("fecha") and m["fecha"][:10] <= hasta.isoformat()]

    conversaciones = await repo.listar_todas_conversaciones()
    conversaciones_periodo = [
        c for c in conversaciones
        if c.get("fecha_inicio") and desde.isoformat() <= c["fecha_inicio"][:10] <= hasta.isoformat()
    ]

    consultas = [m for m in mensajes_periodo if m["rol"] == "usuario"]
    sin_respuesta = [
        m["contenido"] for i, m in enumerate(mensajes_periodo)
        if m["rol"] == "usuario"
        and i + 1 < len(mensajes_periodo)
        and mensajes_periodo[i + 1]["rol"] == "asistente"
        and mensajes_periodo[i + 1]["conversacion_id"] == m["conversacion_id"]
        and any(marcador in mensajes_periodo[i + 1]["contenido"] for marcador in _MARCADORES_SIN_RESPUESTA)
    ]
    pct_con_respuesta = round((1 - len(sin_respuesta) / len(consultas)) * 100, 2) if consultas else 0.0

    conteo_temas: dict[str, int] = {}
    for c in consultas:
        conteo_temas[c["contenido"]] = conteo_temas.get(c["contenido"], 0) + 1
    top_15_temas = sorted(
        [{"tema": k, "frecuencia": v} for k, v in conteo_temas.items()], key=lambda x: x["frecuencia"], reverse=True
    )[:15]

    volumen_por_dia: dict[str, int] = {}
    for c in consultas:
        dia = c["fecha"][:10] if c.get("fecha") else None
        if dia:
            volumen_por_dia[dia] = volumen_por_dia.get(dia, 0) + 1
    volumen_diario = [{"dia": k, "total": v} for k, v in sorted(volumen_por_dia.items())]

    return {
        "total_conversaciones": len(conversaciones_periodo),
        "pct_con_respuesta_verificable": pct_con_respuesta,
        "temas_sin_respuesta": len(set(sin_respuesta)),
        "top_15_temas": top_15_temas,
        "volumen_diario": volumen_diario,
    }
