# Checklist de Validación: Pasajeros (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Pasajeros cumple los RF/RN definidos en `pasajeros-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`pasajeros-spec.md`](./pasajeros-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-PAS-T01 — Segmentación protegida por RBAC.
- [ ] CHK002 RN-PAS-T01 — Solo cuenta reservas confirmadas, no búsquedas.
- [ ] CHK003 RF-PAS-T01 — Filtros se aplican sin botón "Aplicar".
- [ ] CHK004 RN-PAS-T02 — Exportación excluye campos sensibles (documento completo u otros no declarados).

## Trazabilidad de casos de uso

- [ ] CHK005 CU-T04 — prueba automatizada cubre el criterio de aceptación; **bloqueado hasta que `reserva_items` exista con datos reales**.
- [ ] CHK006 CU-T05 — ídem.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
