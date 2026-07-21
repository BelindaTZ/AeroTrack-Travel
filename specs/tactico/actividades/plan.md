# Plan de Implementación — Actividades (Táctico)

**Módulo:** Actividades
**Prefijo:** ACT
**Spec:** [`actividades-spec.md`](./actividades-spec.md)
**Código fuente:** `app/actividades/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. **Nota de secuencia importante:** CU-T42 es precondición real de RF-ACT-006 (Operativo) — no es un "extra táctico" desacoplado como en otros módulos, conviene implementarlo junto con la Fase 2 de `specs/operativo/actividades/plan.md`, no después de cerrar todo el nivel Operativo.

---

## Resumen

Dos CU: configuración de parámetros de disponibilidad sintética (CU-T42, consumida directamente por el nivel Operativo) y reporte de actividades más reservadas (CU-T12, patrón estándar de reporte). Cubre 2 RF y 2 RN. Sin colección propia — ambos leen/escriben `configuracion_sistema` o `reserva_items` (de otros módulos).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2. **Almacenamiento:** `configuracion_sistema` (CU-T42, ya existe, dueño es Seguridad); lectura de `reserva_items` (CU-T12, no implementada todavía).

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Ambos endpoints protegidos por `rbac_service` |
| REG-B3 (cero secretos) | No aplica | Sin credenciales nuevas |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T12 |

Sin violaciones.

---

## Estructura del proyecto

Código propuesto: `app/actividades/router_config_disponibilidad.py` (CU-T42), `app/actividades/router_reporte.py` (CU-T12).

---

## Fases de implementación

### Fase 1 — Configurar disponibilidad sintética (RF-ACT-T01, CU-T42)
**Precondición externa:** ninguna — puede implementarse antes que el nivel Operativo termine, ya que este nivel solo escribe la configuración; RF-ACT-006 (Operativo) es quien la lee. **Recomendado implementar en paralelo con Operativo Fase 2**, no después.
**Entregable:** `router_config_disponibilidad.py`.

### Fase 2 — Reporte de actividades más reservadas (RF-ACT-T02, CU-T12)
**Precondición externa:** `reserva_items` (Reservas, migración pendiente) con datos reales de tipo `actividad`.
**Entregable:** `router_reporte.py`.

---

## Complexity Tracking

*No aplica.*
