# Tasks: Paquetes

**Input:** [`plan.md`](./plan.md) · [`paquetes-spec.md`](./paquetes-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/paquetes/` *(implementado y probado 2026-07-19)*

---

## Fase 0: Precondición

- [x] T001 `reserva_items` (Reservas) existe y está probado (Reservas 1.4, 2026-07-19).
- [x] T002 Crear estructura `app/paquetes/` (`__init__.py`, `services/`, `repositories/`, `tests/` — `templates/` diferido)
- [x] T003 Crear colección `tipos_paquete_descuento` — `scripts/pb_schema_paquetes.py` (esquema ya existía; sembrada con 4 combinaciones reales vía `scripts/seed_tipos_paquete_descuento.py`)
- [x] T004 Crear `app/paquetes/repositories/paquetes_repo.py`
- [x] T005 ~~Crear `app/paquetes/schemas.py`~~ — no fue necesario, mismo criterio que Carrito

---

## Fase 1: Construcción de paquete (RF-PAQ-001, 003, 005)

- [x] T006 `app/paquetes/services/paquete_service.py` — `iniciar_paquete` (componente de vuelo) + `agregar_componente`, acumula en `reserva_items` (CHK001)
- [x] T007 `paquete_service.confirmar_paquete` — valida vuelo+hotel obligatorios antes de confirmar (CHK002, RN-PAQ-001)
- [x] T008 `router_construccion.py` — `PUT /paquetes/{id}/componente/{item_id}`, reemplaza sin afectar los demás (CHK003, REG-J10)
- [x] T009 `router_construccion.py` — `POST /paquetes/{id}/traslado-aeropuerto`, registra en `reserva_extras` con `tipo=traslado_aeropuerto` (CHK004)
- [x] T010 [P] ~~`templates/construir_paquete.html`~~ — diferido, sin pantalla de selección real en las otras verticales todavía
- [x] T011 [P] `app/paquetes/tests/test_paquete_service.py` — construcción con componentes obligatorios y opcionales (CHK001, CHK002), cambio de componente preserva el resto (CHK003), traslado (CHK004), ownership (agregar componente a paquete ajeno rechaza)

**Checkpoint:** ✅ un pasajero construye un paquete completo (motor real, IDs directos de producto).

---

## Fase 2: Resumen y condiciones (RF-PAQ-002, 004)

- [x] T012 `app/paquetes/router_resumen.py` — `GET /paquetes/{id}/resumen`, desglose por componente + descuento aplicable (CHK005)
- [x] T013 `paquete_service.calcular_resumen` — lee `tipos_paquete_descuento` por la combinación exacta de tipos presentes (orden canónico vuelo/hotel/auto/actividad/crucero); `porcentaje_descuento=0.0` si no hay combinación sembrada, nunca falla
- [x] T014 `paquete_service.confirmar_paquete` — copia `descuento_paquete_pct` a `reservas` al confirmar, nunca recalcula retroactivamente (CHK006, RN-PAQ-002); RN-PAQ-004 verificado — cada `reserva_items.precio_final` conserva el precio real (CHK014)
- [x] T015 `paquete_service.condiciones_por_componente` — agrega política de cancelación real de cada componente (vuelo vía `niveles_tarifa`/`politicas_reembolso`, hotel vía `hoteles_tarifas.reembolsable`), sin inventar una política unificada (CHK007)
- [x] T016 [P] ~~`templates/resumen_paquete.html`~~ — diferido
- [x] T017 [P] `app/paquetes/tests/test_paquete_service.py` (mismo archivo que T011) — desglose correcto (CHK005), descuento no cambia tras confirmar (CHK006), condiciones por componente (CHK007), RN-PAQ-004 (CHK014)

**Checkpoint:** ✅ verificado en vivo con datos reales de Vuelos+Hoteles: ahorro real ($500 subtotal → 10% → $450 final) y condiciones reales por componente.

---

## Cierre

- [x] T018 `pytest app/paquetes/` — 9/9 pasan; suite completa (`pytest app/`) sin regresión cruzada
- [x] T019 `checklist.md` repasado; `pendientes-implementacion-codigo.md` actualizado

---

## Dependencias entre fases

- Fase 0 dependía de `reserva_items` (Reservas 1.4) — ya resuelto.
- Fase 2 depende de Fase 1 — ambas completas.
