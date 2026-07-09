# Checklist de Validación: Pasajeros

**Propósito:** Validar que la implementación del módulo Pasajeros cumple los RF/RNF y RN definidos en `pasajeros-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`pasajeros-spec.md`](./pasajeros-spec.md) · [`plan.md`](./plan.md)

---

## Requisitos funcionales

- [ ] CHK001 RF-PAS-001 — El historial muestra únicamente reservas del pasajero autenticado, ordenadas por fecha de vuelo descendente.
- [ ] CHK002 RF-PAS-001 — Cada reserva del historial es navegable a su detalle (CU-O25).
- [ ] CHK003 RF-PAS-002 — Edición de teléfono/dirección/contacto de emergencia funciona sin tocar el correo (fuera de alcance).
- [ ] CHK004 RF-PAS-002 — Confirmación de cambio es inmediata y no bloqueante (REG-J11).
- [ ] CHK005 RF-PAS-003 — Búsqueda de pasajeros por nombre/correo/documento respeta el alcance RBAC Nivel 2 del rol del usuario.
- [ ] CHK006 RF-PAS-004 — Ver/editar detalle de pasajero desde backoffice incluye verificación RBAC (CU-O43) y auditoría (CU-O41).

## Reglas de negocio

- [ ] CHK007 RN-PAS-001 — El documento de identidad, opcional en registro, se exige explícitamente al intentar reservar, no antes.
- [ ] CHK008 RN-PAS-002 — Ninguna funcionalidad bloquea por dato de contacto desactualizado; solo reduce efectividad de notificación (documentado, no impide flujo).
- [ ] CHK009 RN-PAS-003 — Un Agente con restricción de Nivel 2 no puede ver/editar pasajeros fuera de su alcance (prueba explícita con rol restringido).
- [ ] CHK010 RN-PAS-004 — Toda edición de contacto, propia o desde backoffice, queda auditada identificando quién la hizo.

## No funcionales

- [ ] CHK011 RNF-PAS-001 — Filtros de historial (estado, fechas) se aplican sin botón "Aplicar".
- [ ] CHK012 RNF-PAS-002 — Formato de teléfono inválido se rechaza antes de guardar, con mensaje específico.

## Trazabilidad de casos de uso

- [ ] CHK013 CU-O14 — prueba automatizada cubre el criterio de aceptación tal como está en `pasajeros-spec.md`.
- [ ] CHK014 CU-O15 — ídem.
- [ ] CHK015 CU-O16 — ídem, incluyendo el caso de bloqueo por RBAC Nivel 2.

## Notas

- Marcar `[x]` solo con evidencia verificable (prueba, captura, revisión de código).
- Ítems no completables tal como están escritos se registran en `specs/000-sistema-general/errores-conocidos.md`.
