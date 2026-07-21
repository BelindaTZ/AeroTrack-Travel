# Plan de Implementación — Disrupciones y Notificaciones (Táctico)

**Módulo:** Disrupciones y Notificaciones
**Prefijo:** DIS
**Spec:** [`disrupciones-spec.md`](./disrupciones-spec.md)
**Código fuente:** `app/disrupciones/` *(nivel Operativo ya implementado)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. CU-T19/T21 implementables ya; CU-T20 bloqueado por CU-O83 (Operativo, pendiente).

---

## Resumen

Dashboard de monitoreo en tiempo real (CU-T19), configuración de umbral de alerta proactiva por risk score (CU-T20, bloqueado por CU-O83) y reporte de disrupciones por aerolínea/ruta (CU-T21). Cubre 3 RF y 2 RN. Sin colección propia nueva.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** ninguna nueva. **Almacenamiento:** config en `configuracion_sistema`.

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Distinguir Agente (CU-T19) de Administrador (CU-T20, T21) |
| REG-E1/E2 (notificación universal, precedencia) | Sí | RN-DIS-T01 — la alerta proactiva nunca sustituye la reactiva, mantiene la garantía ya establecida en Operativo |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T21 |

Sin violaciones.

---

## Fases de implementación

### Fase 1 — Dashboard de monitoreo (RF-DIS-T01)
**Precondición externa:** ninguna — CU-O27-O31 ya implementados.
**Entregable:** `router_dashboard.py`.

### Fase 2 — Reporte de disrupciones (RF-DIS-T03)
**Precondición externa:** ninguna.
**Entregable:** `router_reporte.py`.

### Fase 3 — Configurar umbral de risk score (RF-DIS-T02)
**Precondición externa:** CU-O83 (Operativo, no implementado) — **bloqueante real**, sin `risk_score` no hay nada que umbralizar de forma significativa. Puede implementarse la UI de configuración antes, pero sin efecto real hasta entonces.
**Entregable:** `router_config_umbral.py`.

---

## Complexity Tracking

*No aplica.*
