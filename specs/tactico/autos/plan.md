# Plan de Implementación — Autos (Táctico)

**Módulo:** Autos
**Prefijo:** AUT
**Spec:** [`autos-spec.md`](./autos-spec.md)
**Código fuente:** `app/autos/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. Depende de `specs/operativo/autos/` y de `reserva_items` (Reservas, migración pendiente).

---

## Resumen

Un único CU: reporte de reservas de autos por proveedor y categoría (CU-T11). Sin colección PocketBase nueva — lee `reserva_items` (Reservas, no implementada todavía) y `autos_catalogo` (Operativo, este módulo).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2, sin librerías nuevas. **Almacenamiento:** solo lectura, ninguna colección propia.

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | `GET /backoffice/autos/reporte` protegido por `rbac_service` |
| REG-J9 (filtros instantáneos) | Sí | Filtro de fecha sin botón "Aplicar" |

Sin violaciones.

---

## Estructura del proyecto

```text
specs/tactico/autos/
├── autos-spec.md
├── plan.md
├── tasks.md
└── checklist.md
```

Código propuesto: `app/autos/router_reporte.py`.

---

## Fases de implementación

### Fase 1 — Reporte de reservas por proveedor y categoría (RF-AUT-T01, CU-T11)
**Precondición externa:** `specs/operativo/autos/` implementado; `reserva_items` (Reservas) con datos reales de tipo `auto`. **Bloqueada hasta entonces** — puede adelantarse con datos de prueba sembrados manualmente, documentando que no cierra de verdad sin la migración de Reservas.
**Entregable:** `router_reporte.py`.

---

## Complexity Tracking

*No aplica.*
