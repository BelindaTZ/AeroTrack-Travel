# Tasks: Facturación

**Input:** [`plan.md`](./plan.md) · [`facturacion-spec.md`](./facturacion-spec.md) · [`checklist.md`](./checklist.md) · [`../../.specify/memory/constitution.md`](../../../.specify/memory/constitution.md)
**Código fuente:** `app/facturacion/` (+ wiring retroactivo en `app/reservas/services/*`)
**Orden de fases:** idéntico al de `plan.md` (Fase 1 → Fase 6), precedido por una Fase 0 de setup.

**Ver "Ajuste de alcance" en `plan.md`** — resumen: checkout con PaymentMethod ID de prueba de Stripe (real, sin Elements/JS de tarjeta), PDF con ReportLab, `pagos.monto` = `total_pagar` completo (sin partición de "cargo de servicio"). Este módulo también **cierra de verdad** los 3 puntos que Reservas dejó documentados como `"pendiente_de_modulo_facturacion"`.

---

## Fase 0: Setup

- [ ] T001 Crear estructura `app/facturacion/` (`__init__.py`, `services/`, `integrations/`, `repositories/`, `templates/`, `templates/backoffice/`, `tests/`)
- [ ] T002 [P] Añadir `stripe` y `reportlab` a `requirements.txt`; instalar en el entorno de desarrollo
- [ ] T003 `app/facturacion/integrations/payment_gateway.py` — única puerta al SDK de Stripe en todo el sistema (REG-F1); lee `stripe.secret_key` de `configuracion_sistema` (nunca hardcodeado, REG-B3); expone `cobrar(monto, metodo_pago_stripe_id, idempotency_key, descripcion)` y `reembolsar(payment_intent_id, monto)`, ambas envueltas en `asyncio.to_thread` (SDK de Stripe es síncrono)
- [ ] T004 [P] `app/facturacion/repositories/facturacion_repo.py` — encapsula consultas de `pagos`, `metodos_pago`, `comisiones`, `remesas`, `remesa_comisiones`, `reembolsos`, `facturas`
- [ ] T005 [P] `app/facturacion/schemas.py` — modelos Pydantic de request/response
- [ ] T006 [P] `app/facturacion/tests/conftest.py` — fixture `pago_factory` (usa `reserva_factory` de Vuelos/Reservas)
- [ ] T007 Añadir `app/facturacion/templates` a `app/shared/templating.py`
- [ ] T008 Smoke test manual (no automatizado, una sola vez): confirmar que `payment_gateway.cobrar()` alcanza la API real de Stripe test mode con las credenciales ya sembradas, antes de construir el resto sobre esa base

**Checkpoint:** conexión real a Stripe test mode confirmada; estructura lista.

---

## Fase 1 — Procesar pago de reserva (RF-FAC-001, RNF-FAC-001/002)

- [ ] T009 `app/facturacion/services/pago_service.py` — `procesar_pago(usuario, reserva_id, metodo_pago_id, escenario_prueba)`: valida que la reserva sea propia y esté `pendiente_pago`; si ya existe un `pagos` `exitoso` para esa reserva, es idempotente y no vuelve a cobrar (RNF-FAC-002); mapea `escenario_prueba` a un PaymentMethod ID de prueba de Stripe; llama `payment_gateway.cobrar(...)` con una `idempotency_key` determinística (`reserva_id` + intento)
- [ ] T010 Si Stripe confirma: crea `pagos` `exitoso`, **llama de verdad** a `app.reservas.services.pago_stub_service.confirmar_pago_reserva(reserva_id)` (cierra el punto de integración real — reutiliza la lógica de RN-RES-005 ya construida y probada, no la duplica)
- [ ] T011 Si Stripe rechaza: crea `pagos` `fallido` con el motivo, no toca la reserva, permite reintentar
- [ ] T012 `app/facturacion/router_pagos.py` — `GET /reservas/{id}/pagar` (desglose de precio visible antes de cobrar, REG-G2; selector de escenario de prueba), `POST /reservas/{id}/pagar`
- [ ] T013 [P] `app/facturacion/templates/checkout_pago.html`
- [ ] T014 Wire `audit_service` en pago exitoso/fallido (CU-O41)
- [ ] T015 [P] `test_pago.py` — pago exitoso marca `pagos.exitoso` y confirma la reserva de verdad (vía `pago_stub_service`, no un mock) (CHK001, CHK016 parcial)
- [ ] T016 [P] `test_pago.py` — pago rechazado marca `fallido`, reserva sigue `pendiente_pago`, permite reintentar
- [ ] T017 `test_pago.py` — RNF-FAC-002: dos llamadas a `procesar_pago` sobre la misma reserva ya pagada no generan un segundo cargo real en Stripe (idempotencia probada contra la API real, no simulada)

**Checkpoint:** una reserva se paga de verdad contra Stripe test mode y queda `confirmada`.

---

## Fase 2 — Factura y comisión (RF-FAC-002, 003)

- [ ] T018 `app/facturacion/services/documentos_service.py` — `generar_pdf_factura(...)`, `generar_pdf_itinerario(...)` con ReportLab; sube el PDF al campo `file` de PocketBase
- [ ] T019 `app/facturacion/services/factura_service.py` — `emitir_factura(pago)`: número de factura único, genera el PDF, crea `facturas`
- [ ] T020 `app/facturacion/services/comision_service.py` — `registrar_comision(pago)`: `monto = pago.monto * aerolinea.comision_pactada_pct / 100`, crea `comisiones` en `pendiente_cobro`
- [ ] T021 Wire `factura_service`/`comision_service` dentro de `pago_service.procesar_pago` — se disparan automáticamente tras todo pago exitoso (`<<include>>` CU-O33/O34)
- [ ] T022 [P] `test_factura_comision.py` — pago exitoso genera factura con PDF y comisión `pendiente_cobro` con el monto correcto (CHK002, CHK003)

**Checkpoint:** todo pago exitoso deja factura y comisión reales, sin pasos manuales.

---

## Fase 3 — Consultar y descargar documentos (RF-FAC-008, 009, 010)

- [ ] T023 `app/facturacion/router_pagos.py` — `GET /pagos` (historial propio, filtra por pasajero autenticado — CHK007)
- [ ] T024 `app/facturacion/router_documentos.py` — `GET /facturas/{id}/pdf` (verifica que la factura pertenezca a una reserva propia antes de servir el archivo)
- [ ] T025 `app/facturacion/router_documentos.py` — `GET /reservas/{id}/itinerario-pdf` (genera on-demand si no existe, usando datos reales de Vuelos/Reservas)
- [ ] T026 [P] `app/facturacion/templates/historial_pagos.html`
- [ ] T027 [P] `test_documentos.py` — historial solo muestra pagos propios; descarga de factura/itinerario ajenos da 404

**Checkpoint:** un pasajero ve su historial y descarga sus documentos reales.

---

## Fase 4 — Reembolso (RF-FAC-006, RN-FAC-001)

- [ ] T028 `app/facturacion/services/reembolso_service.py` — `procesar_reembolso(reserva_id, motivo)`: busca el `pagos` exitoso de la reserva, resuelve la política de la tarifa comprada (vía `VuelosRepository`), calcula el monto exacto (`RN-FAC-001` — sin override manual posible en la firma de la función), llama `payment_gateway.reembolsar(...)` real, crea `reembolsos`
- [ ] T029 `app/facturacion/router_backoffice.py` (o `router_pagos.py`) — `POST /internal/reembolsos`
- [ ] T030 **Wire retroactivo**: `app/reservas/services/cancelar_reserva_service.py` deja de solo auditar `"pendiente_de_modulo_facturacion"` y llama de verdad a `reembolso_service.procesar_reembolso(...)` cuando la política de la tarifa permite reembolso
- [ ] T031 [P] `test_reembolso.py` — reembolso según política real de la tarifa, procesado vía Stripe test mode real (CHK006 de este módulo)
- [ ] T032 [P] `test_reembolso.py` — reembolso fuera de política (0%) no se procesa, sin ninguna vía de override manual
- [ ] T033 En `app/reservas/tests/test_cancelar_reserva.py`: actualizar el test que verificaba el marcador `"pendiente_de_modulo_facturacion"` para confirmar el reembolso real ahora que existe

**Checkpoint:** cancelar una reserva con política de reembolso dispara un reembolso real en Stripe test mode — cierra el primer punto pendiente de Reservas.

---

## Fase 5 — Diferencia de tarifa (RF-FAC-007, CU-O47)

- [ ] T034 `app/facturacion/services/diferencia_tarifa_service.py` — `cobrar_o_reembolsar_diferencia(reserva_id, monto_diferencia)`: si `> 0`, nuevo `pagos` por el monto exacto (mismo mecanismo que Fase 1); si `< 0`, nuevo `reembolsos` por el monto exacto (mismo mecanismo que Fase 4, monto = diferencia, no el total)
- [ ] T035 `app/facturacion/router_diferencia.py` — `POST /internal/reservas/{id}/diferencia-tarifa`
- [ ] T036 **Wire retroactivo**: `app/reservas/services/modificar_reserva_service.py` deja de solo auditar `"pendiente_de_modulo_facturacion"` y llama de verdad a `diferencia_tarifa_service.cobrar_o_reembolsar_diferencia(...)`
- [ ] T037 [P] `test_diferencia_tarifa.py` — diferencia positiva genera un cobro adicional real; diferencia negativa genera un reembolso parcial real, nunca el total de la reserva (CHK009)
- [ ] T038 En `app/reservas/tests/test_modificar_reserva.py`: actualizar el test del marcador para confirmar el cobro/reembolso real

**Checkpoint:** modificar una reserva con cambio de precio cobra/reembolsa la diferencia exacta de verdad — cierra el segundo punto pendiente de Reservas.

---

## Fase 6 — Conciliación y remesas (RF-FAC-004, 005)

- [ ] T039 `app/facturacion/router_backoffice.py` — `GET /backoffice/comisiones` (filtro instantáneo por estado/aerolínea, REG-J9), `POST /backoffice/comisiones/{id}/marcar-cobrada` (RBAC + auditoría, RN-FAC-003: nunca revierte `cobrada` → `pendiente_cobro`)
- [ ] T040 `app/facturacion/services/remesa_service.py` — `generar_remesa(aerolinea_id, periodo)`: agrupa comisiones `cobrada` de esa aerolínea/periodo sin remesa previa, crea `remesas` + `remesa_comisiones`
- [ ] T041 `app/facturacion/router_backoffice.py` — `POST /backoffice/remesas`
- [ ] T042 [P] `app/facturacion/templates/backoffice/comisiones.html`, `backoffice/remesas.html`
- [ ] T043 [P] `test_conciliacion_remesa.py` — marcar cobrada actualiza estado+fecha, RBAC obligatorio, no se puede revertir por esta vía (CHK004)
- [ ] T044 [P] `test_conciliacion_remesa.py` — remesa agrupa el monto total correcto de comisiones cobradas de una aerolínea/periodo (CHK005)

**Checkpoint:** un Administrador concilia comisiones y genera remesas simuladas — módulo Facturación funcionalmente completo.

---

## Cierre

- [ ] T045 Grep de verificación de cero secretos hardcodeados sobre `app/facturacion/`
- [ ] T046 Correr suite completa `pytest app/` (los 4 módulos) para confirmar cero regresión cruzada
- [ ] T047 Repasar `checklist.md` de Facturación; actualizar `reservas/checklist.md` y `errores-conocidos.md` para cerrar los 3 puntos de integración ahora reales (pago, reembolso, diferencia de tarifa); documentar lo que sigue pendiente (Disrupciones → CU-O37, todavía fuera de alcance)

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 bloquea Fase 2 (necesita pagos reales) y es precondición de Fase 4/5 (reutilizan el mismo mecanismo de cobro).
- Fase 3 depende de Fase 2 (necesita facturas reales).
- Fase 4 y Fase 5 son independientes entre sí; ambas dependen de Fase 1.
- Fase 6 depende de Fase 2 (necesita comisiones reales) y de Seguridad Fase 2 (RBAC, ya completa).
