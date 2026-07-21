# Plan de Implementación — Cuenta de Usuario / Mis Viajes

**Módulo:** Cuenta / Mis Viajes
**Prefijo:** CTA
**Spec:** [`cuenta-mis-viajes-spec.md`](./cuenta-mis-viajes-spec.md)
**Código fuente:** `app/cuenta/` *(no existe todavía, salvo CU-O91 en `app/reservas/`)*
**Fecha:** 2026-07-18
**Estado:** ✅ Implementado 2026-07-19 (`app/cuenta/`, 21 tests). CU-O91 sigue en Reservas (ver spec, decisión consciente de no reubicar).

---

## Resumen

Panel de autogestión del pasajero: historial agregado de viajes, favoritos, búsquedas recientes, viajes personalizados, alerta de precio (ya implementada en Reservas) y programa de beneficios. Cubre 6 RF y 3 RN sobre 6 CU (CU-O87–O92). Dueño de `favoritos`, `busquedas_recientes` (en lectura — la escritura es de cada módulo de producto), `viajes_personalizados`, `programa_beneficios_movimientos`.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2. **Almacenamiento:** PocketBase — dueño de 3 colecciones propias + lector de `busquedas_recientes` (escrita por otros módulos) y de `reservas`/`reserva_items` (Reservas). **Restricciones:** RN-CTA-002 — puntos vencidos nunca cuentan en el saldo mostrado.

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-B4 (auditoría) | Sí | Favoritos/viajes personalizados/alertas auditan |
| REG-G1 (autoservicio) | Sí | Todo el módulo es de autoservicio del pasajero, sin intervención de agente |

Sin violaciones.

---

## Estructura del proyecto

```text
app/cuenta/
├── __init__.py
├── router_mis_viajes.py     # RF-CTA-001
├── router_favoritos.py      # RF-CTA-002
├── router_busquedas.py      # RF-CTA-003 (lectura + relanzar)
├── router_viajes_personalizados.py  # RF-CTA-004
├── router_puntos.py         # RF-CTA-006
├── schemas.py
├── services/
│   └── cuenta_service.py
├── repositories/
│   └── cuenta_repo.py
├── templates/
│   └── mis_viajes.html, favoritos.html, mi_cuenta_puntos.html
└── tests/
    ├── test_mis_viajes.py
    ├── test_favoritos.py
    └── test_puntos.py
```

**Nota:** CU-O91 (alerta de precio) no aparece en esta estructura — ya vive en `app/reservas/router_alertas.py` (nombre real a confirmar contra el código). Al implementar este módulo, decidir si se mueve o se re-expone desde aquí; no duplicar.

---

## Fases de implementación

### Fase 1 — Ver Mis Viajes (RF-CTA-001)
**Precondición externa:** `reserva_items` (Reservas, migración pendiente) — bloqueante real.
**Entregable:** `router_mis_viajes.py`.

### Fase 2 — Favoritos y viajes personalizados (RF-CTA-002, 004)
**Precondición externa:** ninguna — implementable de inmediato, sin depender de `reserva_items`.
**Entregable:** `router_favoritos.py`, `router_viajes_personalizados.py`.

### Fase 3 — Búsquedas recientes (RF-CTA-003)
**Precondición externa:** cada módulo de producto (Vuelos, Hoteles, Autos, Actividades, Cruceros) debe escribir en `busquedas_recientes` al ejecutar una búsqueda (RN-CTA-001) — **no está en el alcance actual de esos módulos, hay que retrofitarlo** cuando se implemente cada uno, o agregarlo aquí como tarea cruzada.
**Entregable:** `router_busquedas.py`.

### Fase 4 — Programa de beneficios (RF-CTA-006)
**Precondición externa:** `specs/tactico/cuenta-mis-viajes/` (CU-T24) para los niveles; sin eso, valor por defecto documentado en código.
**Entregable:** `router_puntos.py`.

---

## Complexity Tracking

*No aplica.*
