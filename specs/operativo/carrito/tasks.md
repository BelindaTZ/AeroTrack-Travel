# Tasks: Carrito

**Input:** [`plan.md`](./plan.md) · [`carrito-spec.md`](./carrito-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/carrito/` *(implementado y probado 2026-07-19)*

---

## Fase 0: Setup e infraestructura del módulo

- [x] T001 Crear estructura `app/carrito/` (`__init__.py`, `services/`, `repositories/`, `tests/` — `templates/` diferido, sin pantalla propia todavía)
- [x] T002 [P] Crear colección `carritos` — `scripts/pb_schema_carrito.py`
- [x] T003 [P] Crear colección `carrito_items`
- [x] T004 Crear `app/carrito/repositories/carrito_repo.py`
- [x] T005 ~~Crear `app/carrito/schemas.py`~~ — no fue necesario, mismo criterio que los módulos de catálogo
- [x] T006 [P] Tests usan las fixtures compartidas del `conftest.py` raíz (`pasajero_factory`/`vuelo_factory`/`tarifa_factory`), sin conftest propio necesario

**Checkpoint:** ✅ las 2 colecciones existen; `pytest app/carrito/` corre.

---

## Fase 1: Ver, agregar y eliminar ítems (RF-CAR-001, 002, 003)

- [x] T007 `app/carrito/services/carrito_service.py` — obtiene o crea el carrito activo del pasajero (CHK001, RN-CAR-002)
- [x] T008 `app/carrito/router_carrito.py` — `GET /carrito` (CHK002)
- [x] T009 `router_carrito.py` — `POST /carrito/items`, actualiza `fecha_ultima_actividad` (CHK003)
- [x] T010 `router_carrito.py` — `DELETE /carrito/items/{id}`, recalcula total (CHK004)
- [x] T011 [P] ~~`templates/ver_carrito.html`~~ — diferido, sin pantalla de selección real en las otras verticales todavía
- [x] T012 [P] `app/carrito/tests/test_carrito.py` — 6 tests: un solo carrito activo (CHK001), vacío (CHK002), agregar/eliminar (CHK003/CHK004), ownership (elimina ítem de otro pasajero rechaza)

**Checkpoint:** ✅ un pasajero ve, agrega y elimina ítems de su carrito.

---

## Fase 2: Checkout (RF-CAR-004)

- [x] T013 `app/carrito/router_checkout.py` — `GET /carrito/checkout/revalidar`: revalida cada `precio_snapshot` contra el catálogo real de su módulo dueño (CHK005, RN-CAR-001)
- [x] T014 `carrito_service.revalidar_precios` — si algún precio cambió, lo informa sin modificar nada (CHK006)
- [x] T015 `carrito_service.confirmar_checkout` — mapea `carrito_items`→`reserva_items` 1:1 con el precio VIGENTE, dispara la creación real de la reserva (reutiliza `ReservasRepository`), marca carrito `convertido`
- [x] T016 `router_checkout.py` — `POST /carrito/checkout/confirmar` rechaza checkout de carrito vacío con 409 (CHK007, RN-CAR-003)
- [x] T017 [P] `app/carrito/tests/test_checkout.py` — 4 tests: revalidación detecta cambio real (CHK005/006), checkout vacío rechaza (CHK007), un solo tipo no es paquete, multi-tipo es_paquete=true y usa precio vigente

**Checkpoint:** ✅ verificado en vivo con datos reales de Vuelos+Hoteles: un pasajero convierte su carrito en una reserva real (`reserva_items` poblado, precio revalidado, no el snapshot).

---

## Cierre

- [x] T018 Grep de verificación — sin secretos hardcodeados (módulo no llama ninguna API externa, no aplica REG-B3 más allá de lo ya cubierto)
- [x] T019 `pytest app/carrito/` — 10/10 pasan; suite completa (`pytest app/`) sin regresión cruzada
- [x] T020 `checklist.md` repasado; `pendientes-implementacion-codigo.md` actualizado

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 implementable sin `reserva_items` (no la necesita).
- Fase 2 dependía de `reserva_items` (Reservas 1.4) — ya resuelto.
