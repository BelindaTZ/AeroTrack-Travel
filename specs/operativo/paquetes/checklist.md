# Checklist de Validación: Paquetes

**Propósito:** Validar que la implementación del módulo Paquetes cumple los RF/RN definidos en `paquetes-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`paquetes-spec.md`](./paquetes-spec.md) · [`plan.md`](./plan.md)
**Estado:** Implementado y probado (2026-07-19) — 9/9 tests (`pytest app/paquetes/`), sobre `reserva_items` real (Reservas 1.4).

---

## Requisitos funcionales

- [x] CHK001 RF-PAQ-001 — Construcción de paquete acumula componentes de distintos tipos en `reserva_items`. `test_iniciar_paquete_crea_reserva_con_un_solo_item`, `test_agregar_hotel_activa_es_paquete_y_recalcula_total`.
- [x] CHK002 RN-PAQ-001 — No se puede confirmar un paquete sin vuelo y hotel. `test_confirmar_paquete_sin_hotel_rechaza` (`ComponenteObligatorioFaltante`).
- [x] CHK003 RF-PAQ-003 — Reemplazar un componente no afecta a los demás ya seleccionados. `test_cambiar_componente_no_afecta_los_demas`.
- [x] CHK004 RF-PAQ-005 — Traslado aeropuerto se registra en `reserva_extras` con `tipo=traslado_aeropuerto`. `test_agregar_traslado_aeropuerto`.
- [x] CHK005 RF-PAQ-002 — Resumen desglosa precio por componente, descuento aplicable y precio final. `test_calcular_resumen_desglosa_ahorro_vuelo_hotel` (subtotal $500, 10%, ahorro $50, final $450 — sembrado real en `tipos_paquete_descuento`).
- [x] CHK006 RN-PAQ-002 — El descuento copiado al confirmar no cambia si la configuración cambia después. Verificado por diseño: `confirmar_paquete` escribe `descuento_paquete_pct` en la reserva (valor propio, no una referencia); `test_confirmar_paquete_copia_descuento_y_aplica_precio_final` confirma el valor queda fijo en la reserva.
- [x] CHK007 RF-PAQ-004 — Condiciones/cancelación se muestran por componente, no como política única. `test_condiciones_por_componente_trae_datos_reales` (política real de vuelo vía `niveles_tarifa`, `reembolsable` real de `hoteles_tarifas` — nunca inventadas).
- [x] CHK014 RN-PAQ-004 — El descuento nunca reduce el precio real de cada componente (lo absorbe la agencia, no el proveedor). `test_confirmar_paquete_copia_descuento_y_aplica_precio_final` verifica que `reserva_items.precio_final` de cada componente sigue siendo el precio real ($200/$300) después de confirmar — el descuento vive solo en `reservas.total_pagar`.

## Reglas de negocio

- [x] RN-PAQ-001 — cubierto por CHK002 arriba.
- [x] RN-PAQ-002 — cubierto por CHK006 arriba.
- [x] RN-PAQ-004 — cubierto por CHK014 arriba.
- [x] CHK008 RN-PAQ-003 — Toda mutación de este módulo queda auditada (CU-O41). `router_construccion.py`/`router_resumen.py` llaman `AuditService().insertar(...)`.

## Trazabilidad de casos de uso

- [x] CHK009 CU-O76 — prueba automatizada cubre el criterio de aceptación.
- [x] CHK010 CU-O77 — ídem.
- [x] CHK011 CU-O78 — ídem.
- [x] CHK012 CU-O79 — ídem.
- [x] CHK013 CU-O80 — ídem.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- **Alcance no cubierto en esta ronda:** igual que Carrito, los componentes se agregan por ID directo — no hay una pantalla de construcción de paquete guiada (paso a paso) todavía, solo el motor real (`paquete_service.py`) que la alimentaría.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
