# Tasks: Autos

**Input:** [`plan.md`](./plan.md) · [`autos-spec.md`](./autos-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/autos/` *(Fase 1 implementada y verificada en vivo 2026-07-19)*
**Orden de fases:** idéntico al de `plan.md` (Fase 1 → 3), precedido por una Fase 0 de setup.

---

## Fase 0: Setup e infraestructura del módulo

- [x] T001 Crear estructura `app/autos/` (`__init__.py`, `services/`, `repositories/`, `tests/` — `templates/` diferido a Fase 2)
- [x] T002 Crear colección `autos_catalogo` en `pocketbase-travel` — vía `scripts/pb_schema_autos.py`
- [x] T003 Crear `app/autos/repositories/autos_repo.py`
- [x] T004 ~~Crear `app/autos/schemas.py`~~ — no fue necesario en Fase 1, mismo criterio que Hoteles
- [x] T005 [P] Sembrar credenciales de Global Rental Cars en `configuracion_sistema` (categoría `autos`) — `scripts/seed_autos_config.py`
- [x] T006 [P] `app/autos/tests/conftest.py` — doble determinista `RentalCarsClientFalso`

**Checkpoint:** ✅ la colección existe; `pytest app/autos/` corre.

---

## Fase 1: Generación de catálogo (RF-AUT-004)

- [x] T007 `app/autos/services/rentalcars_client.py` — cliente de **Expedia únicamente** (Priceline/Booking quedan documentados como fuente secundaria futura, no implementados — tienen bugs reales confirmados de fecha/ubicación ignorada, RN-AUT-001). Forma real de la respuesta (árbol de "cards" tipo GraphQL) confirmada en vivo y distinta a lo que sugería la doc previa — ver `errores-conocidos.md`.
- [x] T008 `app/autos/services/catalogo_service.py` — orquesta la sincronización con Expedia (CHK001)
- [x] T009 `dags/dag_generar_catalogo_autos.py` — thin DAG (`@daily`), mismo patrón que Hoteles/Vuelos
- [x] T010 [P] `app/autos/tests/test_catalogo_service.py` — 5 tests: camino feliz, idempotencia (reemplaza ofertas viejas por ciudad+agregador), tarjeta sin precio (no crea oferta, no es error), ciudad no resoluble, falla completa

**Checkpoint:** ✅ el catálogo se puebla con datos reales — verificado en vivo: 25/25 ofertas reales de Expedia para Paris (Opel Mokka $63/día, VW T-Roc, Peugeot 2008/3008, BMW X1, etc.); `sincronizaciones_log` registra la corrida.

---

## Fase 2: Búsqueda, detalle y filtros (RF-AUT-001, 002, 003)

**Estado:** ✅ Hecho 2026-07-19.

- [x] T011 `app/autos/router_busqueda.py` — `GET /autos/buscar` (CHK002)
- [x] T012 `app/autos/router_busqueda.py` — `GET /autos/{id}` (CHK003)
- [x] T013 Filtros instantáneos (categoría, transmisión, precio; **marca/proveedor/kilometraje omitidos** — sin dato real discriminante en el catálogo, ver CHK004/CHK005) (REG-J9)
- [x] T014 [P] `app/autos/templates/buscar_autos.html`, `detalle_auto.html` — reutilizan los componentes genéricos de v3 (`search-layout`, `at-card`, `btn-at-accent`) ya usados por Vuelos, sin CSS nuevo
- [x] T015 [P] `app/autos/tests/test_busqueda.py` — 7 tests: sin resultados, con resultados, case-insensitive, filtros instantáneos, filtro de precio, detalle con especificaciones, 404

**Checkpoint:** ✅ un pasajero busca por ciudad (case-insensitive), filtra por categoría/transmisión/precio y ve el detalle de un vehículo con datos reales.

---

## Fase 3: Selección (RF-AUT-005) — vía Carrito

**Decisión de alcance (2026-07-19):** en vez de un `router_seleccion.py`/`seleccion_service.py` propios, la selección real de Autos se resuelve reutilizando el motor genérico de Carrito (`app/carrito/`, completo desde 2026-07-19) — el botón "Agregar al carrito" en `detalle_auto.html` postea a `/carrito/agregar` (nueva vista HTML sobre `carrito_service.py`, ver `app/carrito/router_vista.py`). Esto evita duplicar lógica de revalidación/auditoría que Carrito ya tiene probada, y conecta Autos con Reservas de punta a punta (`reserva_items`) sin código nuevo en este módulo.

- [x] T016 ~~`seleccion_service.py` con revalidación via `fuente_oferta_ref`~~ — **no implementado.** La revalidación real que existe es la genérica de Carrito (`RN-CAR-001`, compara contra `autos_catalogo` vigente, no contra una llamada en vivo a Expedia). Documentado como brecha abierta en `checklist.md` CHK006 — solo relevante en la práctica si algún día se implementa Priceline/Booking (RN-AUT-001).
- [x] T017 Modalidad de pago — ya viene resuelta desde el catálogo real (`modalidad_pago_disponible`), se muestra en `detalle_auto.html` (CHK007)
- [x] T018 ~~`router_seleccion.py`~~ — reemplazado por `app/carrito/router_vista.py` (`POST /carrito/agregar`, `/carrito/eliminar/{id}`, `/carrito/confirmar`), compartido por todas las verticales de producto
- [x] T019 Integración real con `reserva_items` — verificada en vivo con datos reales (auto real → carrito → checkout → `reserva_items.tipo_producto=auto`)
- [x] T020 [P] `app/carrito/tests/test_vista.py` — agregar/ver/eliminar (CHK015), checkout crea reserva real con `auto_id` (CHK015), checkout vacío no revienta

**Checkpoint:** ✅ un pasajero agrega un auto real al carrito, lo ve, lo elimina o confirma la compra — reserva real creada. La revalidación en vivo contra `fuente_oferta_ref` específica de RN-AUT-001 sigue sin código (bajo riesgo real: solo Expedia implementado, sin el bug de Priceline/Booking).

---

## Cierre

- [x] T021 Grep de verificación de cero secretos hardcodeados sobre `app/autos/` — sin hallazgos
- [x] T022 `pytest app/autos/ app/carrito/` (26/26) y suite completa `pytest app/` sin regresión cruzada
- [x] T023 `checklist.md` repasado; `pendientes-implementacion-codigo.md` actualizado

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 bloquea Fase 2 (necesita catálogo poblado) — resuelto.
- Fase 3 se resolvió reutilizando Carrito en vez de construir un router propio — ver decisión de alcance arriba.
