# Plan de Implementación — Cuenta de Usuario / Mis Viajes (Táctico)

**Módulo:** Cuenta / Mis Viajes
**Prefijo:** CTA
**Spec:** [`cuenta-mis-viajes-spec.md`](./cuenta-mis-viajes-spec.md)
**Código fuente:** `app/cuenta/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. CU-T24 es precondición real de RF-CTA-006 (Operativo).

---

## Resumen

Configuración del programa de beneficios (CU-T24, consumida directamente por el nivel Operativo) y reporte de efectividad de alertas de precio (CU-T25). Cubre 2 RF y 2 RN. `programa_beneficios_niveles` es la única colección propia de este nivel.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2. **Almacenamiento:** dueño de `programa_beneficios_niveles`; lector de `alertas_precio` (Reservas) para CU-T25.

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Ambos endpoints protegidos |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T25 |

Sin violaciones.

---

## Fases de implementación

### Fase 1 — Configurar programa de beneficios (RF-CTA-T01, CU-T24)
**Precondición externa:** ninguna — implementar en paralelo con Operativo Fase 4, no después.
**Entregable:** `router_programa_beneficios.py`, colección `programa_beneficios_niveles`.

### Fase 2 — Reporte de alertas de precio (RF-CTA-T02, CU-T25)
**Precondición externa:** `alertas_precio` (ya implementada en Reservas) con datos reales; reservas confirmadas para medir conversión.
**Entregable:** `router_reporte_alertas.py`.

---

## Complexity Tracking

*No aplica.*
