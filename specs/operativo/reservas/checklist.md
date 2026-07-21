# Checklist de Validación: Reservas

**Propósito:** Validar que la implementación del módulo Reservas cumple los RF/RNF y RN definidos en `reservas-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`reservas-spec.md`](./reservas-spec.md) · [`plan.md`](./plan.md)
**Cerrado (primera pasada de implementación):** 2026-07-09 — 21/21 tests de este módulo pasando (92/92 en todo el sistema: Seguridad+Vuelos+Reservas), verificado además con un flujo real de punta a punta en el contenedor Docker (buscar vuelo → reservar → checkout → detalle → mis reservas → cancelar). Ver "Notas de cierre" al final — Pasajeros no existe en esta sesión.
**Actualizado 2026-07-09 (tras implementar Facturación):** los 3 puntos de integración que quedaban documentados como `"pendiente_de_modulo_facturacion"` (pago, reembolso al cancelar, cobro/reembolso de diferencia al modificar) están cerrados de verdad — ver CHK015/CHK026 abajo.

---

## Requisitos funcionales

- [x] CHK001 RF-RES-001 — Crear reserva autoservicio invoca verificación de cupo antes de crear el registro; sin cupo, no crea nada y explica el motivo.
- [x] CHK002 RF-RES-002 — Crear reserva asistida exige RBAC de Agente/Administrador y registra `agente_id`.
- [x] CHK003 RF-RES-003 — Modificar reserva bloquea si está `cancelada`/`completada`.
- [x] CHK004 RF-RES-003 — Modificación que cambia el precio registra el monto exacto de la diferencia y dispara de verdad el cobro/reembolso contra Facturación (`diferencia_tarifa_service`, ver Notas de cierre).
- [x] CHK005 RF-RES-004 — Cancelar reserva de un vuelo `completado` se bloquea con el mensaje exacto de la fuente.
- [x] CHK006 RF-RES-004 — Cancelación calcula el reembolso solo si la política de tarifa lo permite y lo dispara de verdad contra Stripe test mode vía `reembolso_service.procesar_reembolso` (probado contra la política real de la tarifa, no hardcodeado).
- [x] CHK007 RF-RES-005 — Consulta de estado muestra únicamente reservas propias; una reserva ajena da 404 (ni su existencia se revela).
- [x] CHK008 RF-RES-006 — Alerta de precio se crea en estado `activa` con los campos obligatorios.
- [x] CHK009 RF-RES-007 — Proceso automático cancela reservas `pendiente_pago` vencidas y libera su cupo.

## Reglas de negocio

- [x] CHK010 RN-RES-001 — Ninguna reserva se crea/modifica sin que el servicio de cupo de Vuelos confirme disponibilidad (probado contra `cupo_service` real, no mockeado).
- [x] CHK011 RN-RES-002 — El registro de diferencia de tarifa ocurre únicamente cuando el precio efectivamente cambió — probado el caso negativo explícito (solo extras/misma tarifa no dispara nada).
- [x] CHK012 RN-RES-003 — Cancelación bloqueada si el vuelo ya está `completado`.
- [x] CHK013 RN-RES-004 — Expiración automática libera exactamente el cupo que había tomado, ni más ni menos.
- [x] CHK014 RN-RES-005 — Prueba de condición de carrera real (QP-04, `asyncio.gather` sobre pago y expiración concurrentes): la reserva nunca queda huérfana. Encontrada y corregida una condición de carrera genuina en el proceso (ver Notas de cierre) — el lock por `reserva_id` es lo que hace la garantía real, no solo la lógica de estados.
- [x] CHK015 RN-RES-006 — `total_pagar` refleja el monto vigente a la última confirmación de pago. Se prueba que `total_pagar` se recalcula correctamente al modificar (CHK004) **y** que el cobro real de la diferencia contra Stripe test mode coincide exactamente con ese monto (`app/reservas/tests/test_modificar_reserva.py::test_modificar_cambia_tarifa_cobra_la_diferencia_exacta_de_verdad`).

## No funcionales

- [x] CHK016 RNF-RES-001 — Si el precio cambió entre selección y confirmación, se rechaza sin cobrar ni tocar cupo; nunca se cobra un monto no visto por el pasajero.
- [x] CHK017 RNF-RES-002 — Ventana de expiración se lee de `configuracion_sistema` (`reserva.expiracion_minutos`, ya sembrado en 15) con fallback documentado en código.

## Trazabilidad de casos de uso

- [x] CHK018 CU-O21 — prueba automatizada cubre el criterio de aceptación.
- [x] CHK019 CU-O22 — ídem.
- [x] CHK020 CU-O23 — ídem, incluyendo el registro condicional de la diferencia de precio.
- [x] CHK021 CU-O24 — ídem, incluyendo el bloqueo por vuelo completado.
- [x] CHK022 CU-O25 — ídem.
- [x] CHK023 CU-O26 — ídem.
- [x] CHK024 CU-O44 — ídem.
- [x] CHK025 CU-O45 (RN, orquestación) — prueba de integración confirma que `cupo_service` real de Vuelos se invoca antes de cada creación/modificación (no mockeado, PocketBase real).
- [x] CHK026 CU-O47 (RN, disparador) — el monto exacto de la diferencia está probado (CHK004/CHK011) **y** Facturación lo recibe y procesa de verdad (`app/facturacion/tests/test_diferencia_tarifa.py`, prueba de integración cruzada con Stripe test mode real).

## Trazabilidad — extensión de catálogo v3.0 (2026-07-18, no implementada)

- [ ] CHK027 RF-RES-008 (CU-O81) — consultar requisitos de visa/documentación por destino. *(no implementado)*
- [ ] CHK028 RF-RES-009 (CU-O82) — descargar voucher de reserva en PDF. *(no implementado)*
- [ ] CHK029 CU-O114–O117 (selección de asiento, `<<extend>>` de CU-O21/O22/O23) — no implementado en este módulo; ver `specs/operativo/vuelos/checklist.md` para el estado del lado de Vuelos.
- [x] CHK030 Migración de esquema `reservas`→`reserva_items` polimórfico (dbml v3) — dual-write implementado 2026-07-19 (`crear_reserva_service.py`, `modificar_reserva_service.py`, `cancelar_reserva_service.py`); `reservas.vuelo_id`/`tarifa_id` ahora `required=false`. Desbloquea Paquetes/Carrito/Cuenta-Mis-Viajes. Los 4 puntos de lectura legados (aquí + Facturación) quedan sin tocar a propósito — ver nota en `reservas-spec.md`.

## Notas de cierre — sesión de implementación (2026-07-09)

- **Pasajeros no existe** — este módulo solo maneja al pasajero titular (el usuario autenticado, o el que el Agente identifica por correo). Agregar acompañantes a una reserva (varios `reserva_pasajeros`) queda fuera de esta sesión.
- **Facturación ahora existe y consume estos 3 puntos de verdad (actualizado 2026-07-09)** — `services/pago_stub_service.confirmar_pago_reserva(reserva_id)` es llamado de verdad por `app/facturacion/services/pago_service.procesar_pago` tras un cargo real en Stripe test mode; `cancelar_reserva_service.py` llama a `app.facturacion.services.reembolso_service.procesar_reembolso(...)`; `modificar_reserva_service.py` llama a `app.facturacion.services.diferencia_tarifa_service.cobrar_o_reembolsar_diferencia(...)`. Los tres son llamadas in-process directas (mismo patrón de dependencia transversal usado en todo el sistema), probadas con cargos/reembolsos reales — ver `specs/operativo/facturacion/checklist.md`.
- **Bug real encontrado y corregido durante la implementación**: la primera versión de `pago_stub_service`/`expiracion_service` NO tenía protección contra la condición de carrera que se supone debían resolver — ambas funciones leían el estado de la reserva y escribían sin ningún mecanismo de exclusión mutua, lo que permitía (en una intercalación real de corrutinas) que un pago confirmara una reserva justo después de que la expiración ya la había cancelado y liberado su cupo, dejando una reserva "confirmada" sin cupo real detrás. Corregido agregando `services/reserva_locks.py` (mismo patrón que `cupo_service` de Vuelos) y protegiendo ambas rutas con el mismo lock por `reserva_id`.
- **CHK015/CHK026** quedan ahora completamente cubiertos tras la implementación de Facturación (ver arriba).

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Ítems no completables tal como están escritos se registran en `specs/000-sistema-general/errores-conocidos.md`.
