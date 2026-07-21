# Checklist de Validación: Autos

**Propósito:** Validar que la implementación del módulo Autos cumple los RF/RNF y RN definidos en `autos-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`autos-spec.md`](./autos-spec.md) · [`plan.md`](./plan.md)
**Estado:** Fase 1 (catálogo, 2026-07-19) y Fase 2 (búsqueda/detalle/filtros, 2026-07-19) implementadas y verificadas. Selección (CU-O64) funciona vía Carrito (`/carrito/agregar`), pero la revalidación en vivo contra `fuente_oferta_ref` específica de RN-AUT-001 (Priceline/Booking) sigue sin código — ver nota en CHK006/CHK008.

---

## Requisitos funcionales

- [x] CHK001 RF-AUT-004 — Generación de catálogo prioriza Expedia sobre Priceline/Booking cuando está disponible. Solo Expedia implementado (RN-AUT-001: Priceline/Booking tienen bugs reales de fecha/ubicación ignorada, quedan como fuente secundaria futura, no construida). Verificado en vivo (25 ofertas reales, Paris) y con 5 tests (`test_catalogo_service.py`, doble determinista).
- [x] CHK002 RF-AUT-001 — Búsqueda por ciudad/aeropuerto/fechas filtra el catálogo; sin resultados muestra mensaje claro. `GET /autos/buscar`, `ciudad_recogida~"..."` (case-insensitive). Fechas de recogida/devolución se capturan en el formulario pero no filtran el catálogo (el dato real de Expedia no trae disponibilidad por fecha, mismo criterio que Vuelos con escalas no implementables). 7 tests (`test_busqueda.py`).
- [x] CHK003 RF-AUT-002 — Detalle de vehículo muestra especificaciones, categoría, transmisión y ciudad de recogida. **Proveedor comercial real y política de cancelación NO se muestran** — `proveedor_comercial_id`/`politica_reembolso_id` existen en el esquema pero `catalogo_service.py` (Fase 1) nunca los completa (RNF-AUT-002: no resuelve comisión en esta fase); el detalle solo puede mostrar lo que el catálogo real contiene.
- [x] CHK004 RF-AUT-003 — Filtros (categoría, transmisión, precio máximo) instantáneos sin botón "Aplicar" (`setFiltro()` auto-submit). **Marca y proveedor NO se filtran** — `marca` queda siempre vacío en el catálogo real (ver `errores-conocidos.md`) y solo existe un `proveedor_agregador` (Expedia) en los datos reales, sin valor discriminante.
- [x] CHK005 RF-AUT-003 — No aplica todavía: el catálogo real no expone kilometraje en ningún registro, así que no hay columna que excluir/incluir — comportamiento correcto por ausencia total del dato, no un caso probado explícitamente.
- [ ] CHK006 RF-AUT-005 — **Parcial.** La selección (`/carrito/agregar`, botón "Agregar al carrito" en `detalle_auto.html`) revalida el precio contra `autos_catalogo` vigente al momento del checkout (RN-CAR-001, genérico de Carrito) — pero NO hace una llamada en vivo a Global Rental Cars con `fuente_oferta_ref` como pide la letra de RN-AUT-001. Como solo Expedia está implementado (sin el bug de fecha/ubicación de Priceline/Booking), el riesgo real es bajo, pero la revalidación live contra la fuente sigue sin código.
- [x] CHK007 RF-AUT-005 — Solo existe una modalidad de pago por oferta en el catálogo real (`modalidad_pago_disponible`, poblada desde el proveedor) — nunca se ofrece una que el proveedor no soportó para esa oferta específica.

## Reglas de negocio

- [ ] CHK008 RN-AUT-001 — **Abierto.** Priceline/Booking no están implementados (Fase 1, decisión de alcance), así que el caso "revalidar antes de cobrar para agregadores con bug conocido" no tiene código que probar todavía.
- [x] CHK009 RN-AUT-002 — Toda mutación de este módulo (agregar/eliminar del carrito, checkout) queda auditada vía `AuditService` en `app/carrito/router_vista.py` (mismo patrón que el resto del sistema).
- [ ] RN-AUT-003 — cubierto por CHK007 arriba.

## No funcionales

- [x] CHK010 RNF-AUT-001 — Cada oferta registra internamente su `proveedor_agregador` de origen (`autos_catalogo.proveedor_agregador`).
- [x] CHK011 RNF-AUT-002 — El job de catálogo no escribe fuera de `autos_catalogo` (verificado en `catalogo_service.py`, Fase 1).

## Trazabilidad de casos de uso

- [x] CHK012 CU-O61 — cubierto por `test_busqueda.py` (búsqueda con/sin resultados, case-insensitive).
- [x] CHK013 CU-O62 — cubierto por `test_busqueda.py` (detalle con especificaciones reales, 404 si no existe).
- [x] CHK014 CU-O63 — cubierto por `test_busqueda.py` (filtro de categoría y precio máximo).
- [ ] CHK015 CU-O64 — **Parcial.** Selección funciona de punta a punta vía Carrito (verificado con datos reales: agregar → ver → eliminar → checkout → reserva creada, `app/carrito/tests/test_vista.py`), pero sin la revalidación en vivo contra la fuente que pide RF-AUT-005 en su forma estricta (ver CHK006).
- [x] CHK016 CU-O119 — ídem, incluyendo verificación de registro en `sincronizaciones_log` (Fase 1, 2026-07-19).

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Cualquier ítem no completable tal como está escrito se registra en `specs/000-sistema-general/errores-conocidos.md`.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
