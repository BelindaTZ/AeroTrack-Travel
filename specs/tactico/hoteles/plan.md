# Plan de Implementación — Hoteles (Táctico)

**Módulo:** Hoteles
**Prefijo:** HOT
**Spec:** [`hoteles-spec.md`](./hoteles-spec.md)
**Código fuente:** `app/hoteles/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión antes de iniciar implementación. Depende de que `specs/operativo/hoteles/` esté implementado primero (ver Dependencias).

---

## Resumen

Dos funcionalidades de valor agregado sobre el catálogo/reservas de Hoteles ya operativo: comparación de hasta 5 propiedades para el pasajero, y reporte de hoteles más reservados para el Administrador. Cubre 2 RF y 2 RN sobre 2 CU (CU-T09, CU-T10). Ninguna requiere colección PocketBase nueva — ambas leen datos de colecciones ya definidas en el nivel Operativo (`hoteles_catalogo`, `hoteles_tarifas`) o en Reservas (`reserva_items`, todavía no implementada).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2, mismo stack que el resto del sistema; ninguna librería nueva.
**Almacenamiento:** PocketBase — este nivel no es dueño de ninguna colección, solo lee.
**Pruebas:** pytest + `httpx.AsyncClient`, mismo patrón.
**Restricciones:** RF-HOT-T01 no debe consultar HotelLens de nuevo (RNF-HOT-T01) — reutiliza datos ya cacheados.
**Escala/alcance:** el nivel táctico más pequeño del catálogo — 2 RF, 2 endpoints.

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-J9 (filtros instantáneos) | Sí | RF-HOT-T02 sin botón "Aplicar" |
| REG-B1 (RBAC) | Sí (CU-T10 solamente) | `GET /backoffice/hoteles/reporte` protegido por `rbac_service`, mismo patrón que otros reportes de backoffice |
| REG-F1 (integración reemplazable) | No aplica | Este nivel no llama a ninguna API externa directamente |

Sin violaciones — no se llena Complexity Tracking.

---

## Estructura del proyecto

```text
specs/tactico/hoteles/
├── hoteles-spec.md
├── plan.md
├── tasks.md
└── checklist.md
```

Código propuesto: `app/hoteles/router_comparacion.py` (CU-T09), `app/hoteles/router_reporte.py` (CU-T10) — mismo paquete `app/hoteles/` del nivel Operativo, routers separados porque son funcionalidades de nivel distinto (igual criterio que separa `specs/operativo/` de `specs/tactico/` a nivel de documentación).

---

## Fases de implementación

### Fase 1 — Comparación de propiedades (RF-HOT-T01, CU-T09)
**Precondición externa:** `specs/operativo/hoteles/` Fase 1-2 completas (catálogo poblado, búsqueda funcionando).
**Entregable:** `router_comparacion.py`.

### Fase 2 — Reporte de hoteles más reservados (RF-HOT-T02, CU-T10)
**Precondición externa:** Reservas con `reserva_items` implementado (migración pendiente, ver `reservas-spec.md`) y reservas reales de tipo `hotel` existentes. **Bloqueada hasta entonces** — se puede desarrollar antes con datos de prueba sembrados manualmente, pero no cierra de verdad sin la migración de Reservas.
**Entregable:** `router_reporte.py`.

---

## Complexity Tracking

*No aplica.*
