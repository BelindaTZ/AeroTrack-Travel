# Checklist de Validación: Reservas

**Propósito:** Validar que la implementación del módulo Reservas cumple los RF/RNF y RN definidos en `reservas-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`reservas-spec.md`](./reservas-spec.md) · [`plan.md`](./plan.md)

---

## Requisitos funcionales

- [ ] CHK001 RF-RES-001 — Crear reserva autoservicio invoca verificación de cupo antes de crear el registro; sin cupo, no crea nada y explica el motivo.
- [ ] CHK002 RF-RES-002 — Crear reserva asistida exige RBAC de Agente y registra `agente_id`.
- [ ] CHK003 RF-RES-003 — Modificar reserva revalida cupo si cambia vuelo/tarifa, y bloquea si está `cancelada`/`completada`.
- [ ] CHK004 RF-RES-003 — Modificación que cambia el precio dispara el cobro/reembolso de la diferencia (CU-O47).
- [ ] CHK005 RF-RES-004 — Cancelar reserva de un vuelo `completado` se bloquea con el mensaje exacto de la fuente.
- [ ] CHK006 RF-RES-004 — Cancelación dispara reembolso solo si la política de tarifa lo permite.
- [ ] CHK007 RF-RES-005 — Consulta de estado muestra únicamente reservas propias del pasajero autenticado.
- [ ] CHK008 RF-RES-006 — Alerta de precio se crea en estado `activa` con los campos obligatorios.
- [ ] CHK009 RF-RES-007 — Proceso automático cancela reservas `pendiente_pago` vencidas y libera su cupo.

## Reglas de negocio

- [ ] CHK010 RN-RES-001 — Ninguna reserva se crea/modifica sin que el servicio de cupo confirme disponibilidad.
- [ ] CHK011 RN-RES-002 — El disparo de diferencia de tarifa ocurre únicamente cuando el precio efectivamente cambió — prueba explícita del caso donde no cambia (no debe dispararse nada).
- [ ] CHK012 RN-RES-003 — Cancelación bloqueada si el vuelo ya está `completado`.
- [ ] CHK013 RN-RES-004 — Expiración automática libera exactamente el cupo que había tomado, ni más ni menos.
- [ ] CHK014 RN-RES-005 — Prueba de condición de carrera (QP-04): pago confirmado tras expiración re-confirma la reserva o dispara reembolso inmediato, nunca queda huérfano.
- [ ] CHK015 RN-RES-006 — `total_pagar` refleja el monto vigente a la última confirmación de pago, no el de la selección inicial.

## No funcionales

- [ ] CHK016 RNF-RES-001 — Si el precio cambió entre selección y confirmación, se muestra el nuevo precio antes de cobrar; nunca se cobra un monto no visto por el pasajero.
- [ ] CHK017 RNF-RES-002 — Ventana de expiración se lee de `configuracion_sistema` con fallback documentado de 15 minutos.

## Trazabilidad de casos de uso

- [ ] CHK018 CU-O21 — prueba automatizada cubre el criterio de aceptación.
- [ ] CHK019 CU-O22 — ídem.
- [ ] CHK020 CU-O23 — ídem, incluyendo el disparo condicional de CU-O47.
- [ ] CHK021 CU-O24 — ídem, incluyendo el bloqueo por vuelo completado.
- [ ] CHK022 CU-O25 — ídem.
- [ ] CHK023 CU-O26 — ídem.
- [ ] CHK024 CU-O44 — ídem.
- [ ] CHK025 CU-O45 (RN, orquestación) — prueba de integración confirma que el servicio de cupo de Vuelos se invoca antes de cada creación/modificación.
- [ ] CHK026 CU-O47 (RN, disparador) — prueba de integración confirma que Facturación recibe el monto exacto de la diferencia.

## Notas

- CHK014 y CHK025/CHK026 son pruebas de integración cruzada — requieren que Vuelos y Facturación tengan sus fases correspondientes implementadas; no se marcan `[x]` con mocks permanentes.
- Ítems no completables tal como están escritos se registran en `specs/000-sistema-general/errores-conocidos.md`.
