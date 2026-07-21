# Checklist de Validación: Autos (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Autos cumple RF-AUT-T01/RN-AUT-T01 de `autos-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`autos-spec.md`](./autos-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-AUT-T01 — Reporte protegido por RBAC (solo Administrador).
- [ ] CHK002 RF-AUT-T01 — Agrupa por proveedor y categoría de vehículo.
- [ ] CHK003 RF-AUT-T01 — Filtro de fecha se aplica sin botón "Aplicar" (REG-J9).
- [ ] CHK004 RN-AUT-T01 — Solo cuenta reservas `confirmada` o posterior.

## Trazabilidad de casos de uso

- [ ] CHK005 CU-T11 — prueba automatizada cubre el criterio de aceptación; **bloqueado hasta que `reserva_items` exista con datos reales** — con datos sembrados a mano solo se valida el mecanismo.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- CHK005 no debe cerrarse con datos sembrados a mano como sustituto permanente de datos reales.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
