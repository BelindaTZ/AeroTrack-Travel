# Plan de Implementación — Cruceros (Táctico)

**Módulo:** Cruceros
**Prefijo:** CRU
**Spec:** [`cruceros-spec.md`](./cruceros-spec.md)
**Código fuente:** `app/cruceros/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. **Nota de secuencia:** CU-T43 es precondición real de RF-CRU-006 (Operativo) — implementar junto con esa fase.

---

## Resumen

Dos CU: configuración de disponibilidad sintética de camarotes (CU-T43, consumida directamente por el nivel Operativo) y reporte de cruceros más consultados (CU-T13 — mide interés/búsquedas, no solo reservas confirmadas, a diferencia de los reportes análogos de otras verticales). Cubre 2 RF y 2 RN.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2. **Almacenamiento:** `configuracion_sistema` (CU-T43); para CU-T13, requiere registrar consultas/búsquedas de forma consultable — a definir si es un log liviano propio o se deriva de auditoría existente (ver Fase 2).

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Ambos endpoints protegidos por `rbac_service` |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T13 |

Sin violaciones.

---

## Fases de implementación

### Fase 1 — Configurar disponibilidad sintética (RF-CRU-T01, CU-T43)
**Precondición externa:** ninguna — implementar en paralelo con Operativo Fase 2, no después.
**Entregable:** `router_config_disponibilidad.py`.

### Fase 2 — Reporte de cruceros más consultados (RF-CRU-T02, CU-T13)
**Precondición externa:** decidir mecanismo de registro de consultas/búsquedas antes de implementar — **no asumir que ya existe un log usable**; puede requerir un campo o colección liviana nueva en `specs/operativo/cruceros/` (ej. contador simple o `busquedas_recientes`, ya definido para Cuenta/Mis Viajes pero de otro dominio — evaluar si aplica reutilizarlo o si conviene uno propio de este módulo). A diferencia de los reportes de otras verticales, **no depende de `reserva_items`**.
**Entregable:** `router_reporte.py`.

---

## Complexity Tracking

*No aplica.*
