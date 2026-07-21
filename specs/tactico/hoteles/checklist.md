# Checklist de Validación: Hoteles (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Hoteles cumple los RF/RN definidos en `hoteles-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`hoteles-spec.md`](./hoteles-spec.md) · [`plan.md`](./plan.md)
**Estado:** Módulo nuevo, sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-HOT-T01 — Comparación admite entre 2 y 5 hoteles, mostrando precio desde, estrellas, calificación, category_scores, servicios y política de cancelación.
- [ ] CHK002 RF-HOT-T01 — La comparación no genera ninguna llamada nueva a HotelLens (RNF-HOT-T01).
- [ ] CHK003 RF-HOT-T01 — Un sexto hotel se rechaza explícitamente, sin reemplazar en silencio la selección previa (RN-HOT-T01).
- [ ] CHK004 RF-HOT-T02 — Reporte de hoteles más reservados protegido por RBAC (solo Administrador).
- [ ] CHK005 RF-HOT-T02 — Filtros de destino/período se aplican sin botón "Aplicar" (REG-J9).
- [ ] CHK006 RF-HOT-T02 — Solo cuenta reservas `confirmada` o posterior (RN-HOT-T02).

## Trazabilidad de casos de uso

- [ ] CHK007 CU-T09 — prueba automatizada cubre el criterio de aceptación de `hoteles-spec.md`.
- [ ] CHK008 CU-T10 — ídem; **bloqueado hasta que `reserva_items` (Reservas) exista con datos reales** — con datos de prueba sembrados manualmente se puede validar el mecanismo, no el caso real de negocio.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- CHK008 no debe marcarse `[x]` con datos sembrados a mano como sustituto permanente de datos reales — documentar la diferencia en `errores-conocidos.md` si se cierra así por ahora.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
