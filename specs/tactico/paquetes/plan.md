# Plan de Implementación — Paquetes (Táctico)

**Módulo:** Paquetes
**Prefijo:** PAQ
**Spec:** [`paquetes-spec.md`](./paquetes-spec.md)
**Código fuente:** `app/paquetes/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. **Nota de secuencia:** CU-T14 es precondición real de RF-PAQ-002 (Operativo) — implementar junto con esa fase, no después.

---

## Resumen

Dos CU: configuración de porcentajes de descuento por combinación (CU-T14, consumida directamente por el nivel Operativo) y reporte de combinaciones más vendidas con margen (CU-T15). Cubre 2 RF y 2 RN. Ambos dependen de piezas ya cubiertas en el plan Operativo (`tipos_paquete_descuento`) y de Reservas (`reserva_items`, para CU-T15).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2. **Almacenamiento:** dueño de `tipos_paquete_descuento` (o compartido con Operativo, ver nota de estructura en `specs/operativo/paquetes/plan.md`).

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Ambos endpoints protegidos |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T15 |

Sin violaciones.

---

## Fases de implementación

### Fase 1 — Configurar porcentajes de descuento (RF-PAQ-T01, CU-T14)
**Precondición externa:** ninguna — implementar en paralelo con Operativo Fase 2, no después.
**Entregable:** `router_tipos_descuento.py`.

### Fase 2 — Reporte de combinaciones más vendidas (RF-PAQ-T02, CU-T15)
**Precondición externa:** `reserva_items`/`reservas.es_paquete` (Reservas, migración pendiente) con datos reales.
**Entregable:** `router_reporte.py`.

---

## Complexity Tracking

*No aplica.*
