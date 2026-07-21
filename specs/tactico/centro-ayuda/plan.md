# Plan de Implementación — Centro de Ayuda (Táctico)

**Módulo:** Centro de Ayuda
**Prefijo:** AYU
**Spec:** [`centro-ayuda-spec.md`](./centro-ayuda-spec.md)
**Código fuente:** `app/centro_ayuda/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** ✅ Implementado 2026-07-19 (8 tests de backoffice). RBAC de dos niveles real: Nivel 2 restringe a Agente a `casos_escalados`, dejando artículos/métricas solo a Administrador.

---

## Resumen

Gestión de la base de conocimiento (CU-T28), métricas de satisfacción (CU-T29) y bandeja de casos escalados (CU-T36, gestionada por Agente, no Administrador). Cubre 3 RF y 2 RN. Sin colección propia nueva — usa las 3 ya definidas en el nivel Operativo.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2; reutiliza el cliente Gmail ya integrado en Operativo (envío) y Disrupciones (monitoreo). **Almacenamiento:** sin colecciones propias.

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | CU-T28/T29 requieren rol Administrador; CU-T36 requiere rol Agente — **verificar que `rbac_service` distingue ambos roles correctamente**, no solo "interno vs. pasajero" |
| REG-J9 (filtros instantáneos) | Sí | Búsqueda de artículos en backoffice, filtro de casos por estado |

Sin violaciones.

---

## Fases de implementación

### Fase 1 — Gestionar base de conocimiento (RF-AYU-T01, CU-T28)
**Precondición externa:** ninguna — implementar antes o junto con Operativo Fase 1, para tener contenido real que buscar.
**Entregable:** `router_gestion_articulos.py`.

### Fase 2 — Gestionar bandeja de casos escalados (RF-AYU-T03, CU-T36)
**Precondición externa:** `specs/operativo/centro-ayuda/` Fase 3 completa (necesita casos escalados reales).
**Entregable:** `router_bandeja_casos.py`.

### Fase 3 — Métricas de satisfacción (RF-AYU-T02, CU-T29)
**Precondición externa:** Fase 1 y 2 completas, más datos reales de uso (calificaciones y casos).
**Entregable:** `router_metricas.py`.

---

## Complexity Tracking

*No aplica.*
