# Checklist de Validación: Facturación

**Propósito:** Validar que la implementación del módulo Facturación cumple los RF/RNF y RN definidos en `facturacion-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`facturacion-spec.md`](./facturacion-spec.md) · [`plan.md`](./plan.md)

---

## Requisitos funcionales

- [ ] CHK001 RF-FAC-001 — Desglose completo de precio se muestra antes de solicitar datos de pago; pago exitoso dispara factura y comisión.
- [ ] CHK002 RF-FAC-001 — Pago rechazado muestra motivo y permite reintentar sin duplicar el intento anterior.
- [ ] CHK003 RF-FAC-002 — Factura se genera automáticamente tras pago exitoso, con PDF descargable.
- [ ] CHK004 RF-FAC-003 — Comisión se registra en `pendiente_cobro` con el monto correcto según `comision_pactada_pct`.
- [ ] CHK005 RF-FAC-004 — Conciliación permite marcar comisión como cobrada, con filtro instantáneo y RBAC.
- [ ] CHK006 RF-FAC-005 — Remesa agrupa correctamente comisiones cobradas de una aerolínea en un periodo.
- [ ] CHK007 RF-FAC-006 — Reembolso evalúa automáticamente la política de la tarifa comprada, sin parámetro de override manual.
- [ ] CHK008 RF-FAC-007 — Diferencia de tarifa procesa exactamente el monto recibido de Reservas, no el total de la reserva.
- [ ] CHK009 RF-FAC-008 — Historial de pagos muestra únicamente pagos del pasajero autenticado.
- [ ] CHK010 RF-FAC-009 — Descarga de factura restringida a facturas de reservas propias.
- [ ] CHK011 RF-FAC-010 — Itinerario/e-ticket descargable incluye datos de vuelo y pasajeros correctos.

## Reglas de negocio

- [ ] CHK012 RN-FAC-001 — Ningún endpoint ni servicio permite aprobar un reembolso fuera de lo calculado por `politicas_reembolso`.
- [ ] CHK013 RN-FAC-002 — Todo movimiento (pago/comisión/remesa/reembolso) es trazable de origen a destino con estado consultable.
- [ ] CHK014 RN-FAC-003 — Una comisión `cobrada` no puede revertirse automáticamente a `pendiente_cobro`.
- [ ] CHK015 RN-FAC-004 — Cargo de servicio (inmediato) y comisión (diferida) nunca se registran como el mismo evento contable.
- [ ] CHK016 RN-FAC-005 — Inspección de esquema confirma que ninguna tabla tiene un campo de número de tarjeta completo.
- [ ] CHK017 RN-FAC-006 — Prueba de condición de carrera: pago confirmado por Stripe para una reserva ya expirada se enlaza a reserva re-confirmada o se marca para reembolso total, nunca queda huérfano.

## No funcionales y seguridad

- [ ] CHK018 RNF-FAC-001 — Ningún log, base de datos ni payload capturado contiene un número de tarjeta completo (auditoría de código + inspección de datos de prueba).
- [ ] CHK019 RNF-FAC-002 — Prueba explícita: reenviar el mismo evento de Stripe (mismo `payment_intent_id`) no duplica el pago ni la comisión.

## Trazabilidad de casos de uso

- [ ] CHK020 CU-O32 — prueba automatizada cubre el criterio de aceptación.
- [ ] CHK021 CU-O33 — ídem.
- [ ] CHK022 CU-O34 — ídem.
- [ ] CHK023 CU-O35 — ídem.
- [ ] CHK024 CU-O36 — ídem.
- [ ] CHK025 CU-O37 — ídem, incluyendo el caso de rechazo automático fuera de política.
- [ ] CHK026 CU-O38 — ídem.
- [ ] CHK027 CU-O39 — ídem.
- [ ] CHK028 CU-O40 — ídem.
- [ ] CHK029 CU-O47 (RF, mecanismo) — prueba de integración cruzada con `reservas-spec.md` confirma el monto exacto recibido y procesado.

## Notas

- CHK017 y CHK029 son pruebas de integración cruzada con Reservas — no se marcan `[x]` con stubs permanentes de ese módulo.
- Ítems no completables tal como están escritos se registran en `specs/000-sistema-general/errores-conocidos.md`.
