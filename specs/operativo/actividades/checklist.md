# Checklist de Validación: Actividades

**Propósito:** Validar que la implementación del módulo Actividades cumple los RF/RNF y RN definidos en `actividades-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`actividades-spec.md`](./actividades-spec.md) · [`plan.md`](./plan.md)
**Estado:** Fase 1-4 completas y verificadas (2026-07-19, cerrado en segunda ronda). Selección (CU-O69) funciona vía Carrito, incluyendo validación real de cupo server-side (`app.shared.cupo_service`, generalizado desde Vuelos) y precio total correcto por participantes (`reserva_items.cantidad`, nuevo campo).

---

## Requisitos funcionales

- [x] CHK001 RF-ACT-004 — Generación de catálogo puebla `actividades_catalogo` con los 3 pasos reales de Travel Advisor (auto-complete → list → get-details legacy). Verificado en vivo y con 5 tests (doble determinista).
- [x] CHK002 RF-ACT-005 — Reseñas embebidas de `get-details` se guardan en `actividades_resenas` sin llamada de API separada. Verificado en vivo: 3 reseñas reales con `published_date` ISO real (no texto relativo, a diferencia de Hoteles).
- [x] CHK003 RF-ACT-001/RN-ACT-001 — `inclusiones`/`punto_encuentro`/`condiciones` quedan `null` salvo curación manual; verificado por inspección de `catalogo_service.py` (nunca los escribe).
- [x] CHK004 RF-ACT-006 — Disponibilidad sintética se genera con los parámetros de `configuracion_sistema.disponibilidad_actividades` (sembrados directo, `scripts/seed_actividades_config.py` — CU-T42/Integraciones sin UI de edición todavía). Verificado en vivo: 42 horarios (14 días × 3/día) con cupo 15.
- [x] CHK005 RN-ACT-002 — El dato sintético nunca se presenta como inventario real de proveedor — no hay ningún campo/flag que lo etiquete como tal en el esquema, mismo criterio de `tarifas_vuelo`. Verificado por inspección.
- [x] CHK006 RF-ACT-001 — `GET /actividades/buscar` filtra `actividades_catalogo` por ciudad (case-insensitive); sin resultados muestra mensaje claro. 7 tests (`test_busqueda.py`).
- [x] CHK007 RF-ACT-002 — Detalle muestra descripción; `inclusiones`/`punto_encuentro`/`condiciones` se omiten cuando son `null` (nunca se muestran vacíos) — verificado por template (`{% if %}` por campo), no hay dato curado real todavía para probarlo con contenido.
- [x] CHK008 RF-ACT-003 — Filtros (categoría, precio máximo, calificación mínima) instantáneos sin botón "Aplicar" (`setFiltro()`). Duración sigue inactivo (RF-ACT-003, sin dato real confirmado).
- [x] CHK009 RF-ACT-009 — Reseñas se muestran con autor, calificación, comentario y fecha ISO real (`fecha_resena`, a diferencia de Hoteles).
- [x] CHK010 RF-ACT-007 — Horarios se muestran agrupados por fecha (selector `<select>` sobre `fechas_disponibles`) con cupo aproximado y precio por persona.
- [x] CHK011 RF-ACT-008 — **Cerrado 2026-07-19 (segunda ronda).** El input `participantes` ahora se postea como `cantidad` (campo nuevo en `carrito_items`/`reserva_items`) — `precio_snapshot` quedó como precio UNITARIO, nunca pre-multiplicado en JS. `carrito_service.confirmar_checkout` calcula `precio_final = precio_unitario_vigente × cantidad`, corrigiendo también el falso positivo que tenía la revalidación de precio cuando `cantidad > 1`.
- [x] CHK012 RF-ACT-008 — **Cerrado 2026-07-19.** `carrito_service.confirmar_checkout` verifica y reserva cupo real (`app.shared.cupo_service.verificar_y_reservar_cupo`, generalizado desde Vuelos) por la `cantidad` exacta antes de crear la reserva — todo o nada: si el cupo no alcanza, se lanza `CupoInsuficiente`, se libera cualquier cupo ya reservado en el mismo intento y no se crea ninguna reserva. Verificado con 3 tests en `app/carrito/tests/test_cupo.py` (decremento exacto, rechazo cuando no alcanza, todo-o-nada con dos ítems).

## Reglas de negocio

- [x] RN-ACT-001 — cubierto por CHK003 arriba.
- [x] RN-ACT-002 — cubierto por CHK005 arriba.
- [x] CHK013 RN-ACT-003 — Toda mutación (agregar/eliminar del carrito, checkout) queda auditada vía `AuditService` en `app/carrito/router_vista.py` (compartido con las otras 4 verticales).

## No funcionales

- [x] CHK014 RNF-ACT-001 — El job de catálogo no escribe fuera de `actividades_catalogo`/`actividades_resenas`/`actividades_horarios` (verificado en `catalogo_service.py`).

## Trazabilidad de casos de uso

- [x] CHK015 CU-O65 — cubierto por `test_busqueda.py` (búsqueda con/sin resultados).
- [x] CHK016 CU-O66 — cubierto por `test_busqueda.py` (detalle con descripción/reseñas/horarios, 404 si no existe).
- [x] CHK017 CU-O67 — cubierto por `test_busqueda.py` (filtro de precio y calificación).
- [x] CHK018 CU-O68 — cubierto por `test_busqueda.py` (filtro de horarios por fecha).
- [x] CHK019 CU-O69 — Selección funciona de punta a punta vía Carrito, cupo real incluido — verificado en vivo (script E2E contra Docker: 3 participantes agregados, cupo 5→2, reserva creada con `cantidad=3` y `precio_final=60.0`).
- [x] CHK020 CU-O70 — cubierto por `test_busqueda.py` (reseñas con autor/comentario).
- [x] CHK021 CU-O120 — cubierto por `test_catalogo_service.py` (Fase 1, 5 tests).
- [x] CHK022 CU-O121 — cubierto por `test_catalogo_service.py` (disponibilidad sintética en el mismo ciclo).

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Cualquier ítem no completable tal como está escrito se registra en `specs/000-sistema-general/errores-conocidos.md`.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
