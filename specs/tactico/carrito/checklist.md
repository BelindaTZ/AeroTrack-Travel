# Checklist de Validación: Carrito (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Carrito cumple los RF/RN definidos en `carrito-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`carrito-spec.md`](./carrito-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-CAR-T01 — Configuración protegida por RBAC.
- [ ] CHK002 RF-CAR-T01 — Umbral de inactividad y plantilla se guardan en `configuracion_sistema`.
- [ ] CHK003 RF-CAR-T01 — Carrito inactivo más allá del umbral se marca `abandonado` y dispara el email.
- [ ] CHK004 RN-CAR-T01 — Un carrito `convertido` nunca se marca `abandonado`.
- [ ] CHK005 RF-CAR-T02 — Reporte protegido por RBAC.
- [ ] CHK006 RF-CAR-T02 — Filtro de período se aplica sin botón "Aplicar".
- [ ] CHK007 RN-CAR-T02 — Tasa de recuperación cuenta solo carritos que pasaron por `abandonado` y luego se convirtieron.

## Trazabilidad de casos de uso

- [ ] CHK008 CU-T26 — prueba automatizada cubre el criterio de aceptación.
- [ ] CHK009 CU-T27 — ídem.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
