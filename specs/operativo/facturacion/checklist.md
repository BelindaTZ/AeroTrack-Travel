# Checklist de Validación: Facturación

**Propósito:** Validar que la implementación del módulo Facturación cumple los RF/RNF y RN definidos en `facturacion-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`facturacion-spec.md`](./facturacion-spec.md) · [`plan.md`](./plan.md)

---

## Requisitos funcionales

- [x] CHK001 RF-FAC-001 — Desglose completo de precio se muestra antes de solicitar datos de pago; pago exitoso dispara factura y comisión. (`test_pago.py`, `test_factura_comision.py`)
- [x] CHK002 RF-FAC-001 — Pago rechazado muestra motivo y permite reintentar sin duplicar el intento anterior. (`test_pago.py::test_pago_rechazado_marca_fallido_reserva_sigue_pendiente`)
- [x] CHK003 RF-FAC-002 — Factura se genera automáticamente tras pago exitoso, con PDF descargable. (`test_factura_comision.py`, `test_documentos.py`)
- [x] CHK004 RF-FAC-003 — Comisión se registra en `pendiente_cobro` con el monto correcto según `comision_pactada_pct`. (`test_factura_comision.py`)
- [x] CHK005 RF-FAC-004 — Conciliación permite marcar comisión como cobrada, con filtro instantáneo y RBAC. (`test_conciliacion_remesa.py`; filtro instantáneo en `backoffice/comisiones.html`, no cubierto por prueba automatizada de UI)
- [x] CHK006 RF-FAC-005 — Remesa agrupa correctamente comisiones cobradas de una aerolínea en un periodo. (`test_conciliacion_remesa.py::test_generar_remesa_agrupa_monto_total_correcto`)
- [x] CHK007 RF-FAC-006 — Reembolso evalúa automáticamente la política de la tarifa comprada, sin parámetro de override manual. (`test_reembolso.py`)
- [x] CHK008 RF-FAC-007 — Diferencia de tarifa procesa exactamente el monto recibido de Reservas, no el total de la reserva. (`test_diferencia_tarifa.py`)
- [x] CHK009 RF-FAC-008 — Historial de pagos muestra únicamente pagos del pasajero autenticado. (`test_documentos.py::test_historial_solo_muestra_pagos_propios`)
- [x] CHK010 RF-FAC-009 — Descarga de factura restringida a facturas de reservas propias. (`test_documentos.py::test_descarga_factura_ajena_da_404`)
- [ ] CHK011 RF-FAC-010 — Itinerario/e-ticket descargable incluye datos de vuelo y pasajeros correctos. **Parcial**: incluye reserva/vuelo/aerolínea reales; no incluye nombres de pasajeros individuales — ver nota en `errores-conocidos.md` (Pasajeros fuera de alcance).

## Reglas de negocio

- [x] CHK012 RN-FAC-001 — Ningún endpoint ni servicio permite aprobar un reembolso fuera de lo calculado por `politicas_reembolso`. (`reembolso_service.procesar_reembolso` no acepta monto manual; `test_reembolso.py::test_reembolso_fuera_de_politica_no_se_procesa_sin_override`)
- [x] CHK013 RN-FAC-002 — Todo movimiento (pago/comisión/remesa/reembolso) es trazable de origen a destino con estado consultable. (relaciones `pago_id`/`reserva_id`/`aerolinea_id` reales en las 4 colecciones + `auditoria`)
- [x] CHK014 RN-FAC-003 — Una comisión `cobrada` no puede revertirse automáticamente a `pendiente_cobro`. (`test_conciliacion_remesa.py::test_marcar_cobrada_actualiza_estado_y_no_admite_reversion`)
- [ ] CHK015 RN-FAC-004 — Cargo de servicio (inmediato) y comisión (diferida) nunca se registran como el mismo evento contable. **Fuera de alcance** (ver "Ajuste de alcance" en `plan.md`): `pagos.monto` es el `total_pagar` completo, sin partición de un "cargo de servicio" separado.
- [x] CHK016 RN-FAC-005 — Inspección de esquema confirma que ninguna tabla tiene un campo de número de tarjeta completo. (inspección directa del esquema de `pagos`/`metodos_pago`/`reembolsos` vía API admin; `payment_gateway.py` es el único punto que toca el SDK de Stripe y nunca recibe/almacena un PAN)
- [ ] CHK017 RN-FAC-006 — Prueba de condición de carrera: pago confirmado por Stripe para una reserva ya expirada se enlaza a reserva re-confirmada o se marca para reembolso total, nunca queda huérfano. **No probado esta sesión** — ver `errores-conocidos.md`.

## No funcionales y seguridad

- [x] CHK018 RNF-FAC-001 — Ningún log, base de datos ni payload capturado contiene un número de tarjeta completo (auditoría de código + inspección de datos de prueba). (mismo fundamento que CHK016; checkout usa PaymentMethod IDs de prueba de Stripe, nunca un PAN)
- [ ] CHK019 RNF-FAC-002 — Prueba explícita: reenviar el mismo evento de Stripe (mismo `payment_intent_id`) no duplica el pago ni la comisión. **Ajuste de alcance**: no hay receptor de webhooks de Stripe en esta sesión (checkout síncrono con PaymentMethod IDs de prueba, ver `plan.md`), así que "reenviar el mismo evento" no aplica literalmente. La idempotencia sí está probada en la capa que existe: `test_pago.py::test_pago_idempotente_no_genera_segundo_cargo` (dos llamadas a `procesar_pago` sobre la misma reserva ya pagada no generan un segundo cargo real).

## Trazabilidad de casos de uso

- [x] CHK020 CU-O32 (procesar pago) — `test_pago.py`.
- [x] CHK021 CU-O33 (emitir factura) — `test_factura_comision.py`.
- [x] CHK022 CU-O34 (registrar comisión) — `test_factura_comision.py`.
- [x] CHK023 CU-O35 (marcar comisión cobrada) — `test_conciliacion_remesa.py`.
- [x] CHK024 CU-O36 (generar remesa) — `test_conciliacion_remesa.py`.
- [x] CHK025 CU-O37 (reembolso) — `test_reembolso.py`, incluyendo el caso de rechazo automático fuera de política.
- [x] CHK026 CU-O38 (historial de pagos propio) — `test_documentos.py`.
- [x] CHK027 CU-O39 (descarga de factura) — `test_documentos.py`.
- [x] CHK028 CU-O40 (descarga de itinerario) — `test_documentos.py`.
- [x] CHK029 CU-O47 (RF, mecanismo) — prueba de integración cruzada con `reservas-spec.md` confirma el monto exacto recibido y procesado. (`test_diferencia_tarifa.py` + `app/reservas/tests/test_modificar_reserva.py::test_modificar_cambia_tarifa_cobra_la_diferencia_exacta_de_verdad`)

## Notas

- Los 3 puntos que Reservas dejó documentados como `"pendiente_de_modulo_facturacion"` (pago, reembolso al cancelar, diferencia de tarifa al modificar) están **cerrados de verdad** — `app/reservas/services/cancelar_reserva_service.py` y `modificar_reserva_service.py` llaman ahora a los servicios reales de Facturación in-process, probado con cargos/reembolsos reales contra Stripe test mode.
- CHK011, CHK015, CHK017, CHK019 quedan sin marcar por las razones anotadas arriba — no son fallas de la implementación sino ajustes de alcance o pruebas no cubiertas esta sesión; ver `specs/000-sistema-general/errores-conocidos.md`.
- Disrupciones (CU-O37 disparado por una interrupción de vuelo, no por cancelación voluntaria) sigue fuera de alcance — el reembolso de esta sesión solo cubre el camino voluntario (`cancelar_reserva`).
