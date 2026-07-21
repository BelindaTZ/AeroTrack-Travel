# Plan de Implementación — Ofertas y Promociones (Táctico)

**Módulo:** Ofertas y Promociones
**Prefijo:** OFE
**Spec:** [`ofertas-promociones-spec.md`](./ofertas-promociones-spec.md)
**Código fuente:** `app/ofertas/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** ✅ Implementado 2026-07-19 (8 tests de backoffice). Envío real de SendGrid rechaza explícitamente — sin credencial sembrada, no simulado.

---

## Resumen

Gestión de cupones (CU-T30, consumida directamente por el nivel Operativo), campañas de email real vía SendGrid (CU-T31), reporte de uso de cupones (CU-T32), y configuración de acumulación cupón+paquete (CU-T44, nuevo 2026-07-18, resuelve QP-18). Cubre 4 RF y 4 RN. Sin colección propia nueva — usa las 4 ya definidas en el nivel Operativo más `campanas_email`; CU-T44 solo agrega un campo a `cupones_descuento` (ya reflejado en el dbml v3) y una clave nueva en `configuracion_sistema`.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2; SendGrid (envío real, REG-I5-equivalente para este módulo — mismo proveedor que usan Disrupciones/Carrito para email). **Almacenamiento:** dueño de `campanas_email`.

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Los 3 endpoints protegidos |
| REG-B3 (cero secretos) | Sí | Credenciales SendGrid en `configuracion_sistema` |
| REG-F1 (integración reemplazable) | Sí | Reutiliza el cliente de email ya usado por Disrupciones/Carrito, no crea uno nuevo |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T32 |

Sin violaciones.

---

## Fases de implementación

### Fase 1 — Gestionar cupones (RF-OFE-T01, CU-T30)
**Precondición externa:** ninguna — implementar en paralelo con Operativo Fase 3, no después.
**Entregable:** `router_cupones_admin.py`.

### Fase 2 — Campañas de email (RF-OFE-T02, CU-T31)
**Precondición externa:** credenciales de SendGrid ya configuradas (reutilizadas).
**Entregable:** `router_campanas.py`.

### Fase 3 — Reporte de cupones (RF-OFE-T03, CU-T32)
**Precondición externa:** Fase 1 completa y `cupones_uso` con datos reales (Operativo Fase 3).
**Entregable:** `router_reporte_cupones.py`.

### Fase 4 — Configurar acumulación cupón+paquete (RF-OFE-T04, CU-T44)
**Precondición externa:** Fase 1 completa (el campo por-cupón se edita en la misma pantalla de CU-T30); Operativo Fase 3 (RF-OFE-003) debe leer esta regla antes de aplicar un cupón sobre un paquete — coordinar la entrega de ambas fases.
**Entregable:** campo `acumulable_con_paquete` en el formulario de `router_cupones_admin.py` (Fase 1) + `router_config_acumulacion.py` para el default global.

---

## Complexity Tracking

*No aplica.*
