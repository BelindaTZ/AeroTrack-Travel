# Checklist de Validación: Hoteles

**Propósito:** Validar que la implementación del módulo Hoteles cumple los RF/RNF y RN definidos en `hoteles-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`hoteles-spec.md`](./hoteles-spec.md) · [`plan.md`](./plan.md)
**Estado:** Fase 1, 2 y 3 completas y verificadas (2026-07-19, cerrado en segunda ronda) — catálogo, búsqueda/detalle/filtros/reseñas, comparación reembolsable, cargos locales reales (99 ciudades importadas del CSV de Holidu), y cupo real validado server-side vía Carrito (`app.shared.cupo_service`). Solo Fase 4 — pago diferido (RF-HOT-009) — sigue sin código, depende de CU-O86 (Facturación, tampoco implementado).

---

## Requisitos funcionales

- [x] CHK001 RF-HOT-004 — Generación de catálogo puebla `hoteles_catalogo`/`hoteles_tarifas` con los 3 pasos reales de HotelLens (descubrimiento → comparador → detalle real). Verificado en vivo (Hilton Paris Opera, `hotel_id` Booking.com 54642) y con 4 tests automatizados (`test_catalogo_service.py`, doble determinista para no gastar cuota real en cada corrida de la suite).
- [x] CHK002 RF-HOT-001 — `GET /hoteles/buscar` filtra por ciudad (case-insensitive); sin resultados muestra mensaje claro; precio desde = mínimo de `hoteles_tarifas` vigente. 7 tests (`test_busqueda.py`).
- [x] CHK003 RF-HOT-002 — Detalle muestra descripción, servicios (`servicios`, JSON array), check-in/check-out. **`category_scores` y mapa (`latitud`/`longitud`) tienen sección en el template pero sin dato real que mostrar** — HotelLens no expone `category_scores` en el flujo de 3 pasos usado (confirmado en Fase 1, ver `errores-conocidos.md`); la sección se omite automáticamente por estar vacía, nunca se probó con datos reales.
- [x] CHK004 RF-HOT-003 — Filtros (estrellas mínimas, precio máximo, calificación mínima) instantáneos sin botón "Aplicar". **Servicios/amenidades y zona no se filtran** — sin UI de selección múltiple sobre el JSON array de servicios en esta ronda.
- [x] CHK005 RF-HOT-007 — Reseñas se muestran con autor, calificación/escala, comentario, fecha relativa y fuente libre.
- [x] CHK006 RF-HOT-008 — **Cerrado 2026-07-19 (segunda ronda).** `dags/dag_importar_cargos_locales.py` + `app/hoteles/services/cargos_locales_service.py` parsean el CSV real de Holidu (solo su Tabla 1 — el archivo trae dos tablas concatenadas, confirmado al inspeccionarlo) e importan 99 ciudades reales. Verificado en vivo: Paris muestra su regla real ("5star: €11.38; 4star: €8.45; ..."), correctamente clasificada como compuesta (sin estimado inventado, solo `regla_texto`). 6 tests (`test_cargos_locales.py`).
- [x] CHK007 RF-HOT-006 — Habitaciones muestran reembolsable/no reembolsable como badge explícito (dato real de `hoteles_tarifas.reembolsable`) antes del botón de agregar al carrito.
- [ ] CHK011 RF-HOT-009 — **No implementado.** `hoteles_tarifas` no tiene ningún campo de modalidad de pago diferido en el esquema; fuera de alcance de esta ronda (depende de CU-O86, Facturación, tampoco implementado).

## Reglas de negocio

- [x] CHK008 RN-HOT-001 — **Cerrado 2026-07-19 (segunda ronda), con matiz.** `carrito_service.confirmar_checkout` ahora verifica y reserva cupo real server-side (`app.shared.cupo_service`) antes de crear la reserva — todo o nada. **Matiz:** revalida contra `hoteles_tarifas.cupos_disponibles` (el último valor sincronizado desde HotelLens), no contra una llamada en vivo a HotelLens en el momento exacto del checkout — mismo estándar que el resto del sistema (Vuelos tampoco llama a una fuente externa en vivo, revalida contra su propio catálogo).
- [x] CHK009 RN-HOT-002 — Reembolsable/cancelación son datos reales mostrados directamente (`t.reembolsable`, `t.cancelacion_hasta`); `politica_reembolso_id` nunca se lee en el template (no hay dato curado todavía, comportamiento por defecto correcto — no sustituye nada porque no hay nada que sustituir).
- [x] CHK010 RN-HOT-003 — Repositorio filtra `cargos_locales_destino` por `ciudad` + `activo=true`; con datos reales importados, el comportamiento se verificó en ambos caminos (ciudad cubierta: Paris muestra su regla; ciudad no cubierta: se omite).
- [x] CHK025 RN-HOT-003 — **Cerrado 2026-07-19.** `dags/dag_importar_cargos_locales.py` existe (disparo manual, `schedule=None`, coherente con "los datos no cambian a diario"); corrida real verificada (99 ciudades creadas, 0 duplicados en una segunda corrida idempotente).
- [ ] RN-HOT-004 — cubierto por CHK011 arriba (no implementado).
- [x] CHK012 RN-HOT-005 — Toda mutación (agregar/eliminar del carrito, checkout) queda auditada vía `AuditService` (compartido, `app/carrito/router_vista.py`).

## No funcionales

- [x] CHK013 RNF-HOT-001 — Ciudad/país se muestran tal cual vienen de `hoteles_catalogo` (ya limpios desde Fase 1), sin geocodificación adicional en el template.
- [x] CHK014 RNF-HOT-002 — El job de catálogo no escribe en ninguna colección fuera de las 3 propias de este módulo (más `sincronizaciones_log`). Verificado por inspección de `catalogo_service.py`/`hoteles_repo.py`.

## Trazabilidad de casos de uso

- [x] CHK015 CU-O54 — cubierto por `test_busqueda.py` (búsqueda con precio desde, sin resultados).
- [x] CHK016 CU-O55 — cubierto por `test_busqueda.py` (detalle con descripción/servicios, 404 si no existe).
- [x] CHK017 CU-O56 — cubierto por `test_busqueda.py` (filtro de estrellas y precio).
- [x] CHK018 CU-O57 — Selección funciona de punta a punta vía Carrito, cupo real incluido (verificado en vivo: tarifa real → carrito → checkout → `reserva_items.tipo_producto=hotel`, cupo decrementado).
- [x] CHK019 CU-O58 — cubierto por `test_busqueda.py` (reseñas con autor/comentario).
- [x] CHK020 CU-O59 — datos reales verificados en ambos caminos (ver CHK006/CHK025) — Paris muestra su regla real, ciudades no cubiertas se omiten.
- [ ] CHK021 CU-O60 — no implementado (ver CHK011).
- [x] CHK022 CU-O118 — cubierto por CHK001; 4 tests (Fase 1).

## Diseño de interfaz (constitución, Sección J)

- [x] CHK023 J5 — Layout de conversión: una acción primaria ("Agregar") por habitación, precio y condición (reembolsable) visibles antes de decidir, no una tabla cruda.
- [x] CHK024 J9 — Filtros instantáneos sin botón "Aplicar" (`setFiltro()`).

## Notas

- Marcar `[x]` solo con evidencia verificable (prueba automatizada, captura de pantalla, o revisión de código) — no marcar por inspección visual únicamente.
- Cualquier ítem que no pueda completarse tal como está escrito se registra en `specs/000-sistema-general/errores-conocidos.md`, no se omite en silencio.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md` quitando a Hoteles de la lista de módulos sin código.
