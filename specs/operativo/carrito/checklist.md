# Checklist de Validación: Carrito

**Propósito:** Validar que la implementación del módulo Carrito cumple los RF/RN definidos en `carrito-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`carrito-spec.md`](./carrito-spec.md) · [`plan.md`](./plan.md)
**Estado:** Implementado y probado (2026-07-19) — Fase 1+2 completas, 10/10 tests (`pytest app/carrito/`), incluyendo checkout real hacia `reserva_items`.

---

## Requisitos funcionales

- [x] CHK001 RN-CAR-002 — Un pasajero tiene a lo sumo un carrito activo; ítems nuevos se agregan al existente. `test_agregar_dos_items_reutiliza_el_mismo_carrito`.
- [x] CHK002 RF-CAR-001 — Contenido del carrito muestra cada ítem con precio y total; vacío muestra mensaje claro. `test_ver_carrito_suma_precios_snapshot`, `test_ver_carrito_sin_carrito_activo_devuelve_vacio`.
- [x] CHK003 RF-CAR-002 — Agregar ítem actualiza `fecha_ultima_actividad`. Verificado por inspección (`carrito_service.agregar_item` la actualiza en cada llamada).
- [x] CHK004 RF-CAR-003 — Eliminar un ítem no afecta a los demás; total se recalcula. `test_eliminar_item_no_afecta_los_demas`.
- [x] CHK005 RF-CAR-004 — Checkout revalida cada precio contra el catálogo vigente. `test_confirmar_checkout_multi_tipo_es_paquete_y_usa_precio_vigente` (usa precio vigente de `hoteles_tarifas`, no el snapshot viejo).
- [x] CHK006 RN-CAR-001 — Precio cambiado se informa antes de continuar, nunca se cobra el snapshot desactualizado. `test_revalidar_precios_detecta_cambio_real`.
- [x] CHK007 RN-CAR-003 — Checkout de carrito vacío se rechaza. `test_confirmar_checkout_vacio_rechaza`.

## Reglas de negocio

- [x] RN-CAR-001 — cubierto por CHK006 arriba.
- [x] RN-CAR-002 — cubierto por CHK001 arriba.
- [x] RN-CAR-003 — cubierto por CHK007 arriba.
- [x] CHK008 RN-CAR-004 — Toda mutación de este módulo queda auditada (CU-O41). `router_carrito.py`/`router_checkout.py` llaman `AuditService().insertar(...)` en agregar/eliminar/checkout.

## Trazabilidad de casos de uso

- [x] CHK009 CU-O93 — prueba automatizada cubre el criterio de aceptación.
- [x] CHK010 CU-O94 — ídem.
- [x] CHK011 CU-O95 — ídem.
- [x] CHK012 CU-O96 — ídem; `reserva_items` ya existe (Reservas 1.4, dual-write) — checkout real verificado, no simulado.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- **Alcance no cubierto en esta ronda:** `router_carrito.py` acepta IDs de producto directos en el body — no hay una pantalla de "agregar al carrito" integrada en Hoteles/Autos/Actividades/Cruceros todavía (ninguno tiene su Fase de selección para el pasajero construida). Se completa cuando cada módulo tenga esa pantalla.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
