# Tasks: Actividades

**Input:** [`plan.md`](./plan.md) · [`actividades-spec.md`](./actividades-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/actividades/` *(Fase 1+2 implementadas y verificadas en vivo 2026-07-19)*
**Orden de fases:** idéntico al de `plan.md`, precedido por Fase 0 de setup.

---

## Fase 0: Setup e infraestructura del módulo

- [x] T001 Crear estructura `app/actividades/` (`__init__.py`, `services/`, `repositories/`, `tests/` — `templates/` diferido a Fase 3)
- [x] T002 [P] Crear colección `actividades_catalogo` — `scripts/pb_schema_actividades.py`
- [x] T003 [P] Crear colección `actividades_horarios`
- [x] T004 [P] Crear colección `actividades_resenas`
- [x] T005 Crear `app/actividades/repositories/actividades_repo.py`
- [x] T006 ~~Crear `app/actividades/schemas.py`~~ — no fue necesario, mismo criterio que Hoteles/Autos
- [x] T007 [P] Sembrar credenciales de Travel Advisor en `configuracion_sistema` (categoría `actividades`) — `scripts/seed_actividades_config.py`, incluye también `disponibilidad_actividades.*` (CU-T42 sembrado directo, sin UI todavía)
- [x] T008 [P] `app/actividades/tests/conftest.py` — doble determinista `TravelAdvisorClientFalso`

**Checkpoint:** ✅ las 3 colecciones existen; `pytest app/actividades/` corre.

---

## Fase 1: Generación de catálogo y reseñas (RF-ACT-004, 005) + Fase 2: Disponibilidad sintética (RF-ACT-006)

**Decisión de implementación:** ambas fases se construyeron en un solo `catalogo_service.py`/DAG en vez de archivos separados — sin disponibilidad, una actividad recién catalogada no es reservable (CU-O68/O69), así que generarla en el mismo ciclo evita una ventana donde el catálogo existe pero está incompleto. `disponibilidad_service.py` separado no se creó.

- [x] T009 `app/actividades/services/traveladvisor_client.py` — `locations/v2/auto-complete` + `attraction-products/v2/list` + `attractions/get-details` (legacy, no el `v2/get-details` roto). Nombres de campo verificados en vivo **antes** de escribir la extracción (a diferencia de Hoteles/Autos, que se corrigieron después) — ver `errores-conocidos.md`.
- [x] T010 `app/actividades/services/catalogo_service.py` — orquesta los 3 pasos, guarda catálogo (CHK001)
- [x] T011 `catalogo_service.py` — guarda reseñas embebidas de `get-details` en `actividades_resenas`, sin llamada aparte (CHK002)
- [x] T012 `catalogo_service.py` — `inclusiones`/`punto_encuentro`/`condiciones` quedan `null` salvo curación manual explícita (CHK003, RN-ACT-001)
- [x] T013 `dags/dag_generar_catalogo_actividades.py` — thin DAG (`@daily`)
- [x] T014 [P] `app/actividades/tests/test_catalogo_service.py` — 5 tests: camino feliz (catálogo+reseñas+disponibilidad en un ciclo, CHK001/002), curación manual no se sobrescribe (CHK003), idempotencia, tarjeta sin `lid` resoluble, ciudad no resoluble, falla completa
- [x] T015 `catalogo_service._generar_disponibilidad_sintetica` — genera `actividades_horarios` por regla de negocio, lee `configuracion_sistema.disponibilidad_actividades.*` con default documentado (CHK004)
- [x] T017 (parte) cubierto por T014 — generación con parámetros default (CHK004), sin ningún campo que lo marque como inventario real (CHK005, RN-ACT-002)

**Checkpoint:** ✅ verificado en vivo (Paris Seine River Sightseeing Cruise, 3 reseñas reales, 42 horarios sintéticos con cupo 15); `sincronizaciones_log` registra la corrida.

---

## Fase 3: Búsqueda, detalle, filtros, horarios y reseñas (RF-ACT-001, 002, 003, 007, 009)

**Estado:** ✅ Hecho 2026-07-19.

- [x] T018 `app/actividades/router_busqueda.py` — `GET /actividades/buscar` (CHK006)
- [x] T019 `router_busqueda.py` — `GET /actividades/{id}` (CHK007) — incluye horarios (CHK010, filtrables por `?fecha=`) y reseñas (CHK009) en la misma pantalla, sin sub-rutas separadas
- [x] T020 Filtros instantáneos (categoría, precio, calificación — duración inactivo, ver Fuera de alcance) (REG-J9, CHK008)
- [x] T021 ~~`GET /actividades/{id}/resenas`~~ — reseñas embebidas en el detalle en vez de una sub-ruta propia (CHK009)
- [x] T022 [P] `app/actividades/templates/buscar_actividades.html`, `detalle_actividad.html`
- [x] T023 [P] `app/actividades/tests/test_busqueda.py` — 7 tests: sin resultados (CHK006), con resultados, filtros de precio/calificación (CHK008), detalle con descripción/reseñas/horarios (CHK007/CHK009/CHK010), filtro de horarios por fecha, 404

**Checkpoint:** ✅ un pasajero busca, filtra, ve detalle+reseñas+horarios por fecha de una actividad real (Travel Advisor).

---

## Fase 4: Seleccionar (RF-ACT-008) — vía Carrito

**Decisión de alcance (2026-07-19):** mismo criterio que Autos — sin `seleccion_service.py`/`router_horarios.py` propios. Cada horario en `detalle_actividad.html` tiene un mini-formulario que postea a `/carrito/agregar` (Carrito) con `precio_snapshot = precio_unitario × participantes` (calculado en JS, `prepararEnvio()`, antes del submit).

- [x] T024 ~~`GET /actividades/{id}/horarios`~~ — ya cubierto por el detalle (Fase 3, CHK010)
- [x] T025 Precio total por participantes — calculado client-side antes de postear (CHK011). **No implementado:** validar cupo sintético disponible antes de confirmar (CHK012) — ni el formulario ni `carrito_service.agregar_item` lo verifican, el `max=` del input es solo una pista visual.
- [x] T026 ~~`router_horarios.py`~~ — reemplazado por `app/carrito/router_vista.py` (compartido con las otras 4 verticales)
- [x] T027 Integración real con `reserva_items` — verificada en vivo (horario real → carrito → checkout → `reserva_items.tipo_producto=actividad`)
- [ ] T028 `app/carrito/tests/test_vista.py` cubre agregar/checkout genérico, pero **no hay ningún test que agregue más participantes que `cupos_disponibles`** — no hay comportamiento que probar todavía (CHK012 abierto)

**Checkpoint:** ✅ un pasajero elige fecha/horario/participantes y confirma la compra con precio total correcto — cupo insuficiente NO se valida (brecha documentada, ver CHK012).

---

## Cierre

- [x] T029 Grep de verificación de cero secretos hardcodeados sobre `app/actividades/` — sin hallazgos
- [x] T030 `pytest app/actividades/ app/carrito/` (26/26) y suite completa sin regresión cruzada
- [x] T031 `checklist.md` repasado; `pendientes-implementacion-codigo.md` actualizado

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 bloquea Fase 2 (necesita actividades reales) y Fase 3 (necesita catálogo poblado) — resuelto.
- Fase 4 se resolvió reutilizando Carrito en vez de construir un router propio — ver decisión de alcance arriba. Validación de cupo (CHK012) queda pendiente real, no bloqueada por nada externo.
