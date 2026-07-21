# Checklist de Validación: Seguridad (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Seguridad cumple los RF/RN definidos en `seguridad-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`seguridad-spec.md`](./seguridad-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`. A diferencia de otros niveles Táctico, ninguno de estos 4 CU está bloqueado por una pieza externa — todos reutilizan servicios ya probados del nivel Operativo.

---

## Requisitos funcionales

- [ ] CHK001 RF-SEG-T01 — Dashboard agrupa intentos fallidos por usuario/IP.
- [ ] CHK002 RF-SEG-T01 — Filtros se aplican sin botón "Aplicar".
- [ ] CHK003 RF-SEG-T02 — Forzar expiración invalida realmente las sesiones activas del usuario (verificar contra `session_service`, no solo marcar un flag).
- [ ] CHK004 RN-SEG-T02 — La acción incluye RBAC y auditoría.
- [ ] CHK005 RF-SEG-T03 — Cambio de política se refleja en el comportamiento real de `password_service`/`session_service` sin reiniciar el servicio.
- [ ] CHK006 RF-SEG-T04 — Matriz muestra todos los roles × módulos × tablas correctamente.

## Trazabilidad de casos de uso

- [ ] CHK007 CU-T01 — prueba automatizada cubre el criterio de aceptación.
- [ ] CHK008 CU-T02 — ídem, con verificación real de invalidación de sesión.
- [ ] CHK009 CU-T03 — ídem.
- [ ] CHK010 CU-T35 — ídem.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- CHK005 es un punto de atención real: si `RNF-SEG-007` (Operativo) cachea el valor de política en memoria al arrancar, un cambio desde CU-T03 no tendría efecto hasta reiniciar — verificar explícitamente que lee `configuracion_sistema` en cada uso, no solo al inicio.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
