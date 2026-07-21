# Checklist de Validación: Cruceros

**Propósito:** Validar que la implementación del módulo Cruceros cumple los RF/RNF y RN definidos en `cruceros-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`cruceros-spec.md`](./cruceros-spec.md) · [`plan.md`](./plan.md)
**Estado:** Fase 1-4 completas (2026-07-19, cerrado en segunda ronda) — Carnival/Royal Caribbean reales, precio real por camarote, cupos sintéticos. Selección (CU-O75) funciona vía Carrito con validación real de cupo server-side (`app.shared.cupo_service`, ver CHK008).

---

## Requisitos funcionales

- [x] CHK001 RF-CRU-005 — Generación de catálogo puebla `navieras`/`barcos`/`cruceros_catalogo`/`cruceros_camarotes_tarifa` con datos reales de Cruise Pricing API. Verificado en vivo (Carnival Valor, Anthem of the Seas, precio real por camarote) y con 3 tests (doble determinista).
- [x] CHK002 RF-CRU-006 — Disponibilidad sintética se genera con los parámetros de `configuracion_sistema.disponibilidad_cruceros` (sembrados directo, `scripts/seed_cruceros_config.py`). Verificado en vivo: cupos=20 por camarote.
- [x] CHK003 RN-CRU-001 — El dato sintético nunca se presenta como cupo real de la naviera — reconfirmado en vivo (2026-07-19) que `/cruises/{id}` no expone ningún campo de inventario en toda la respuesta (solo `cabin_prices_per_person`, precio).
- [x] CHK004 RF-CRU-001 — `GET /cruceros/buscar` filtra por destino (substring de puerto en `itinerario_puertos`, insensible a mayúsculas) y por rango de duración; sin resultados muestra mensaje claro. Filtro por fechas de zarpe **no implementado** (solo duración/destino) — 6 tests (`test_busqueda.py`).
- [x] CHK005 RF-CRU-002 — Itinerario se muestra en el orden real del array (`{"day": N, "port": "..."}` — forma real confirmada en vivo, no strings planos como se asumió al escribir el código por primera vez; corregido antes de cerrar esta ronda, ver `errores-conocidos.md`).
- [x] CHK006 RF-CRU-003 — Información del barco muestra servicios (`servicios_abordo`) y políticas (`politicas`) cuando existen; se omite la sección si ambos son `null` (ningún dato real curado todavía, plano de cubierta tampoco se muestra — archivo, fuera de alcance de esta ronda).
- [x] CHK007 RF-CRU-004 — `GET /cruceros/barco/{barco_id}/fechas` compara todas las fechas de zarpe del mismo barco con precio por tipo de camarote lado a lado (tabla).
- [x] CHK008 RF-CRU-007 — **Cerrado 2026-07-19 (segunda ronda).** Además del gate de presentación (botón oculto si `cupos_disponibles=0`), `carrito_service.confirmar_checkout` ahora verifica y reserva cupo real server-side (`app.shared.cupo_service`) antes de crear la reserva — todo o nada, mismo mecanismo que Actividades/Hoteles/Vuelos.

## Reglas de negocio

- [x] RN-CRU-001 — cubierto por CHK003 arriba.
- [x] CHK009 RN-CRU-002 — Toda mutación (agregar/eliminar del carrito, checkout) queda auditada vía `AuditService` (compartido, `app/carrito/router_vista.py`).

## No funcionales

- [x] CHK010 RNF-CRU-001 — El job de catálogo no escribe fuera de las 4 colecciones propias (verificado en `catalogo_service.py`).

## Trazabilidad de casos de uso

- [x] CHK011 CU-O71 — cubierto por `test_busqueda.py` (búsqueda por puerto, filtro de duración).
- [x] CHK012 CU-O72 — cubierto por `test_busqueda.py` (detalle con itinerario real, 404 si no existe).
- [x] CHK013 CU-O73 — cubierto por `test_busqueda.py` (comparar fechas del mismo barco).
- [x] CHK014 CU-O74 — cubierto por `test_busqueda.py` (detalle muestra info de barco cuando existe).
- [x] CHK015 CU-O75 — Selección funciona de punta a punta vía Carrito, cupo real incluido (verificado en vivo: camarote real → carrito → checkout → `reserva_items.tipo_producto=crucero`, cupo decrementado).
- [x] CHK016 CU-O122 — cubierto por `test_catalogo_service.py` (Fase 1, 3 tests).
- [x] CHK017 CU-O123 — cubierto por `test_catalogo_service.py` (disponibilidad sintética en el mismo ciclo).

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Cualquier ítem no completable tal como está escrito se registra en `specs/000-sistema-general/errores-conocidos.md`.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
