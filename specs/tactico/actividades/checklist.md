# Checklist de Validación: Actividades (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Actividades cumple los RF/RN definidos en `actividades-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`actividades-spec.md`](./actividades-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-ACT-T01 — Configuración protegida por RBAC (solo Administrador).
- [ ] CHK002 RF-ACT-T01 — Se guarda en `configuracion_sistema` con `modificado_por` obligatorio, global o por categoría.
- [ ] CHK003 RN-ACT-T01 — Un cambio de configuración no reescribe `actividades_horarios` ya generado.
- [ ] CHK004 RF-ACT-T02 — Reporte protegido por RBAC.
- [ ] CHK005 RF-ACT-T02 — Filtros de destino/categoría se aplican sin botón "Aplicar".
- [ ] CHK006 RN-ACT-T02 — Solo cuenta reservas `confirmada` o posterior.

## Trazabilidad de casos de uso

- [ ] CHK007 CU-T42 — prueba automatizada cubre el criterio de aceptación; verificar además que `specs/operativo/actividades/` (RF-ACT-006) efectivamente lee estos valores una vez implementado.
- [ ] CHK008 CU-T12 — prueba cubre el criterio de aceptación; **bloqueado hasta que `reserva_items` exista con datos reales**.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- CHK007 no cierra completo hasta confirmar la integración real con `disponibilidad_service.py` del nivel Operativo.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
