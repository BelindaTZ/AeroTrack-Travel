# Checklist de Validación: Cuenta de Usuario / Mis Viajes (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico cumple los RF/RN definidos en `cuenta-mis-viajes-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`cuenta-mis-viajes-spec.md`](./cuenta-mis-viajes-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-CTA-T01 — Configuración de niveles protegida por RBAC.
- [ ] CHK002 RN-CTA-T01 — Niveles no se solapan en `puntos_minimos`.
- [ ] CHK003 RF-CTA-T02 — Reporte protegido por RBAC.
- [ ] CHK004 RF-CTA-T02 — Filtro de período se aplica sin botón "Aplicar".
- [ ] CHK005 RN-CTA-T02 — Conversión calculada con atribución aproximada, documentada como tal en el reporte.

## Trazabilidad de casos de uso

- [ ] CHK006 CU-T24 — prueba automatizada cubre el criterio de aceptación; verificar integración real con RF-CTA-006 (Operativo).
- [ ] CHK007 CU-T25 — prueba cubre el criterio de aceptación.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
