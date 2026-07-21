# Checklist de Validación: Cuenta de Usuario / Mis Viajes

**Propósito:** Validar que la implementación de este módulo cumple los RF/RN definidos en `cuenta-mis-viajes-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`cuenta-mis-viajes-spec.md`](./cuenta-mis-viajes-spec.md) · [`plan.md`](./plan.md)
**Estado:** ✅ **Implementado 2026-07-19** — `app/cuenta/`, 21/21 tests. CU-O91 sigue viviendo en Reservas (ver Notas).

---

## Requisitos funcionales

- [x] CHK001 RF-CTA-001 — Mis Viajes agrupa reservas por próxima/activa/pasada con detalle completo. **Limitación real, documentada:** solo vuelo/actividad/crucero aportan fecha resoluble hoy — hotel/auto caen en un 4º grupo honesto "sin fecha" porque Carrito no captura check-in/checkout ni recogida/devolución todavía (ver `errores-conocidos.md`).
- [x] CHK002 RF-CTA-002 — Guardar/eliminar favorito de tipo destino/hotel/actividad. Botón ♥ real en `detalle_hotel.html`, `detalle_actividad.html` e Inicio (destinos populares) — no solo el endpoint, la UI está conectada de punta a punta.
- [x] CHK003 RF-CTA-004 — Crear viaje personalizado con nombre y descripción.
- [x] CHK004 RF-CTA-003 — Búsquedas recientes se pueden relanzar hacia el buscador correspondiente. Los 5 buscadores (`app/shared/busqueda_reciente.py`) ya escriben en `busquedas_recientes` al ejecutar una búsqueda real logueada.
- [x] CHK005 RF-CTA-006 — Saldo de puntos excluye vencidos; historial completo de movimientos. Con 0 niveles/movimientos reales sembrados hoy, el estado vacío se maneja explícitamente (nunca se fabrica un nivel o saldo).

## Reglas de negocio

- [x] RN-CTA-001 — los 5 módulos de producto (Vuelos/Hoteles/Autos/Actividades/Cruceros) escriben `busquedas_recientes` vía el helper compartido; verificado con test que confirma que una búsqueda anónima NO escribe nada.
- [x] RN-CTA-002 — cubierto por CHK005; verificado con test explícito de vencimiento por `vencimiento_meses`.
- [x] CHK006 RN-CTA-003 — Toda mutación de este módulo queda auditada (CU-O41) — favoritos y viajes personalizados via `AuditService`.

## Trazabilidad de casos de uso

- [x] CHK007 CU-O87 — `app/cuenta/tests/test_mis_viajes.py` (6 tests, E2E vía Carrito real).
- [x] CHK008 CU-O88 — `app/cuenta/tests/test_favoritos.py` (4 tests).
- [x] CHK009 CU-O89 — `app/cuenta/tests/test_busquedas.py` (3 tests).
- [x] CHK010 CU-O90 — `app/cuenta/tests/test_viajes_personalizados.py` (3 tests).
- [x] CHK011 CU-O91 — **ya implementado y probado en `app/reservas/`** bajo el número original CU-O26 (ver `specs/operativo/reservas/checklist.md` CHK023). No se reubicó el código en esta ronda — bajo riesgo, no bloqueaba nada.
- [x] CHK012 CU-O92 — `app/cuenta/tests/test_puntos.py` (5 tests, incluye vencimiento).

## Notas

- CHK011 sigue siendo el único ítem que no tiene código propio en este módulo — es una decisión consciente de no reubicar código ya probado, no una brecha.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`. — **hecho**.
