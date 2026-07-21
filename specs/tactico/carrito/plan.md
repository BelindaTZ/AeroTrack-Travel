# Plan de Implementación — Carrito (Táctico)

**Módulo:** Carrito
**Prefijo:** CAR
**Spec:** [`carrito-spec.md`](./carrito-spec.md)
**Código fuente:** `app/carrito/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. Implementable en paralelo con el nivel Operativo (no depende de `reserva_items`).

---

## Resumen

Detección automática de abandono de carrito con recordatorio por email, y reporte de tasa de recuperación. Cubre 2 RF y 2 RN. Sin colección propia — lee/escribe `carritos.estado` (Operativo) y `configuracion_sistema`.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2; reutiliza la capa de envío de email ya usada por Disrupciones. **Almacenamiento:** ninguna colección propia.

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Ambos endpoints protegidos |
| REG-F1 (integración reemplazable) | Sí | Reutiliza la capa de envío de email existente, no crea una nueva integración |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T27 |

Sin violaciones.

---

## Fases de implementación

### Fase 1 — Configurar y detectar abandono (RF-CAR-T01, CU-T26)
**Precondición externa:** `specs/operativo/carrito/` Fase 1 completa (carritos reales con actividad); capa de envío de email ya existente (Disrupciones).
**Entregable:** `router_config_abandono.py`, job programado que marca `carritos.estado = abandonado` y dispara el email.

### Fase 2 — Reporte de recuperación (RF-CAR-T02, CU-T27)
**Precondición externa:** Fase 1 completa (necesita carritos abandonados reales para medir recuperación).
**Entregable:** `router_reporte.py`.

---

## Complexity Tracking

*No aplica.*
