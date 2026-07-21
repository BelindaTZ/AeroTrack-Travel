# Checklist de Validación: Paquetes (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Paquetes cumple los RF/RN definidos en `paquetes-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`paquetes-spec.md`](./paquetes-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-PAQ-T01 — Configuración protegida por RBAC.
- [ ] CHK002 RF-PAQ-T01 — Crea/edita combinación con porcentaje y estado activo.
- [ ] CHK003 RN-PAQ-T01 — Cambios no afectan paquetes ya confirmados.
- [ ] CHK004 RF-PAQ-T02 — Reporte protegido por RBAC.
- [ ] CHK005 RF-PAQ-T02 — Filtro de período se aplica sin botón "Aplicar".
- [ ] CHK006 RN-PAQ-T02 — Solo cuenta paquetes confirmados; margen calculado correctamente.

## Trazabilidad de casos de uso

- [ ] CHK007 CU-T14 — prueba automatizada cubre el criterio de aceptación; verificar que `specs/operativo/paquetes/` (RF-PAQ-002) efectivamente lee estos valores una vez implementado.
- [ ] CHK008 CU-T15 — prueba cubre el criterio de aceptación; **bloqueado hasta que `reserva_items` exista con datos reales**.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
