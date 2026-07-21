# Checklist de Validación: Facturación (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Facturación cumple los RF/RN definidos en `facturacion-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`facturacion-spec.md`](./facturacion-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-FAC-T01 — Dashboard protegido por RBAC.
- [ ] CHK002 RF-FAC-T01 — Ingresos agrupados correctamente por tipo de producto.
- [ ] CHK003 RF-FAC-T01 — Comisiones y remesas pendientes reflejan datos reales.
- [ ] CHK004 RF-FAC-T02 — Reporte protegido por RBAC.
- [ ] CHK005 RF-FAC-T02 — Filtros se aplican sin botón "Aplicar".
- [ ] CHK006 RN-FAC-T01 — Cargo de servicio y comisión se muestran como series separadas, nunca sumadas como el mismo evento contable.

## Reglas de negocio

- [ ] RN-FAC-T01 — cubierto por CHK006 arriba.
- [ ] CHK007 RN-FAC-T02 — El dashboard refleja datos en tiempo real, no un snapshot cacheado sin indicarlo.

## Trazabilidad de casos de uso

- [ ] CHK008 CU-T22 — prueba automatizada cubre el criterio de aceptación.
- [ ] CHK009 CU-T23 — ídem, verificando explícitamente la separación cargo de servicio/comisión.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
