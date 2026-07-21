# Tasks: Cruceros

**Input:** [`plan.md`](./plan.md) · [`cruceros-spec.md`](./cruceros-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/cruceros/` *(Fase 1+2 implementadas y verificadas en vivo 2026-07-19)*
**Orden de fases:** idéntico al de `plan.md`, precedido por Fase 0 de setup.

---

## Fase 0: Setup e infraestructura del módulo

- [x] T001 Crear estructura `app/cruceros/` (`__init__.py`, `services/`, `repositories/`, `tests/` — `templates/` diferido a Fase 3)
- [x] T002 [P] Crear colección `navieras` — `scripts/pb_schema_cruceros.py`
- [x] T003 [P] Crear colección `barcos`
- [x] T004 [P] Crear colección `cruceros_catalogo`
- [x] T005 [P] Crear colección `cruceros_camarotes_tarifa`
- [x] T006 Crear `app/cruceros/repositories/cruceros_repo.py`
- [x] T007 ~~Crear `app/cruceros/schemas.py`~~ — no fue necesario, mismo criterio que los demás módulos de catálogo
- [x] T008 [P] Sembrar credenciales de Cruise Pricing API en `configuracion_sistema` (categoría `cruceros`) — `scripts/seed_cruceros_config.py`, incluye `disponibilidad_cruceros.*`
- [x] T009 [P] `app/cruceros/tests/conftest.py` — doble determinista `CruisePricingClientFalso`

**Checkpoint:** ✅ las 4 colecciones existen; `pytest app/cruceros/` corre.

---

## Fase 1: Generación de catálogo (RF-CRU-005) + Fase 2: Disponibilidad sintética (RF-CRU-006)

**Decisión de implementación:** igual que Actividades — ambas fases en un solo `catalogo_service.py`/DAG, sin disponibilidad un camarote recién catalogado no sería seleccionable.

- [x] T010 `app/cruceros/services/cruisepricing_client.py` — `/cruise-lines`, `/cruises`, `/cruises/{id}`. Nombres de campo verificados en vivo antes de escribir la extracción (`cabin_prices_per_person` confirmado real; reconfirmado que no existe ningún campo de inventario en la respuesta completa).
- [x] T011 `app/cruceros/services/catalogo_service.py` — orquesta la sincronización de las 4 colecciones (CHK001)
- [x] T012 `dags/dag_generar_catalogo_cruceros.py` — thin DAG (`@daily`)
- [x] T013 [P] `app/cruceros/tests/test_catalogo_service.py` — 3 tests: camino feliz (naviera/barco/crucero/camarotes+disponibilidad en un ciclo), idempotencia, falla completa
- [x] T014 `catalogo_service._generar_camarotes` — genera `cupos_disponibles` sintético por crucero×tipo de camarote, lee `configuracion_sistema.disponibilidad_cruceros.*` (CHK002)
- [x] T016 (parte) cubierto por T013 — nunca se marca como inventario real (CHK003, RN-CRU-001)

**Checkpoint:** ✅ verificado en vivo (Carnival Valor $700/persona INTERIOR, Anthem of the Seas €2217, cupos sintéticos=20); `sincronizaciones_log` registra la corrida.

---

## Fase 3: Búsqueda, itinerario, barco y comparación (RF-CRU-001 a 004)

**Estado:** ✅ Hecho 2026-07-19.

- [x] T017 `app/cruceros/router_busqueda.py` — `GET /cruceros/buscar` (CHK004) — filtra por puerto en `itinerario_puertos` y rango de duración; fechas de zarpe no implementado como filtro
- [x] T018 `router_busqueda.py` — `GET /cruceros/{id}` (CHK005) — itinerario + info de barco + camarotes en una sola pantalla, sin sub-rutas `/itinerario`/`/barco` separadas
- [x] T019 ~~`GET /cruceros/{id}/barco`~~ — fusionado con el detalle (CHK006)
- [x] T020 `router_busqueda.py` — `GET /cruceros/barco/{barco_id}/fechas` (CHK007)
- [x] T021 [P] `app/cruceros/templates/buscar_cruceros.html`, `detalle_crucero.html`, `comparar_fechas.html`
- [x] T022 [P] `app/cruceros/tests/test_busqueda.py` — 6 tests: sin resultados (CHK004), búsqueda por puerto, filtro de duración, detalle con itinerario+camarotes (CHK005), 404, comparar fechas del mismo barco (CHK007)

**Bug real encontrado y corregido en esta fase:** `itinerario_puertos` (Cruise Pricing API) es una lista de `{"day": N, "port": "..."}`, no strings planos como asumía el código original de Fase 1 (nunca se había renderizado en pantalla hasta ahora, así que el supuesto no se había puesto a prueba). Se descubrió al verificar en Docker contra el único crucero real del catálogo (`AN07A400_2026-07-20`, Seattle→Alaska) — los puertos se veían como repr de diccionario en vez de texto legible. Corregido en `router_busqueda.py` (`_nombre_puerto()`, acepta ambas formas) y en los fixtures de test. Ver `errores-conocidos.md`.

**Checkpoint:** ✅ un pasajero busca por puerto/duración, ve itinerario real día a día, información del barco y compara fechas de zarpe — verificado en Docker contra el crucero real del catálogo.

---

## Fase 4: Selección de camarote (RF-CRU-007) — vía Carrito

**Decisión de alcance (2026-07-19):** mismo criterio que Autos/Actividades — sin `seleccion_service.py`/`router_seleccion.py` propios. Cada camarote en `detalle_crucero.html` tiene un botón que postea a `/carrito/agregar` (Carrito).

- [ ] T023 `seleccion_service.py` con validación de cupo — **no implementado.** Solo hay gate de presentación (botón oculto si `cupos_disponibles=0`), no hay validación server-side (CHK008)
- [x] T024 ~~`router_seleccion.py`~~ — reemplazado por `app/carrito/router_vista.py` (compartido)
- [x] T025 Integración real con `reserva_items` — verificada en vivo (camarote real → carrito → checkout → `reserva_items.tipo_producto=crucero`)
- [ ] T026 [P] `test_seleccion.py` — no existe; no hay comportamiento de "cupo agotado se rechaza" que probar todavía (CHK008 abierto)

**Checkpoint:** ✅ un pasajero selecciona un tipo de camarote real y confirma la compra — cupo insuficiente NO se valida server-side (brecha documentada).

---

## Cierre

- [x] T027 Grep de verificación de cero secretos hardcodeados sobre `app/cruceros/` — sin hallazgos
- [x] T028 `pytest app/cruceros/ app/carrito/` (24/24) y suite completa sin regresión cruzada
- [x] T029 `checklist.md` repasado; `pendientes-implementacion-codigo.md` actualizado

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 bloquea Fase 2 (necesita cruceros reales) y Fase 3 (necesita catálogo poblado) — resuelto.
- Fase 4 se resolvió reutilizando Carrito en vez de construir un router propio — ver decisión de alcance arriba. Validación de cupo (CHK008) queda pendiente real.
