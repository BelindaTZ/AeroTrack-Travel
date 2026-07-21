# Checklist de Validación: Ofertas y Promociones

**Propósito:** Validar que la implementación del módulo Ofertas y Promociones cumple los RF/RN definidos en `ofertas-promociones-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`ofertas-promociones-spec.md`](./ofertas-promociones-spec.md) · [`plan.md`](./plan.md)
**Estado:** ✅ **Implementado 2026-07-19** — `app/ofertas/`, 28/28 tests. Dos bugs reales encontrados y corregidos durante la verificación en vivo (ver Notas).

---

## Requisitos funcionales

- [x] CHK001 RF-OFE-001 — Ofertas destacadas se filtran por vigencia y estado activo. Verificado en vivo (oferta real vigente vs. una expirada creada en test, la expirada no aparece).
- [x] CHK002 RF-OFE-005 — Términos y condiciones se muestran completos antes de aplicar.
- [x] CHK003 RF-OFE-002/RN-OFE-001 — Destinos populares se calculan por agregación real (`busquedas_recientes` + `reserva_items` de vuelo), nunca se presentan como oferta curada — la plantilla incluye el texto explícito "no es una selección editorial".
- [x] CHK004 RF-OFE-003 — Cupón se valida por vigencia, estado, usos disponibles y producto aplicable — 9 tests cubren cada motivo de rechazo por separado.
- [x] CHK005 RN-OFE-002 — Un cupón no se puede aplicar dos veces a la misma reserva — verificado con test explícito de doble intento.
- [x] CHK006 RF-OFE-004 — Suscripción al newsletter funciona con y sin sesión (asocia `pasajero_id` cuando hay sesión de pasajero).

## Reglas de negocio

- [x] RN-OFE-001 — cubierto por CHK003 arriba.
- [x] RN-OFE-002 — cubierto por CHK005 arriba.
- [x] CHK007 RN-OFE-003 — Acumulación cupón+paquete evalúa excepción del cupón → default global, en ese orden; verificado con 2 tests (default global `false` rechaza, excepción `true` en el cupón individual gana sobre el default).
- [x] CHK008 RN-OFE-004 — Canje de cupón y suscripción quedan auditados vía `AuditService`.

## Trazabilidad de casos de uso

- [x] CHK009 CU-O101 — `app/ofertas/tests/test_ofertas.py` (4 tests) + verificado en vivo con oferta real (vuelo real como `producto_ref`, resuelto a "Vuelo WN1111").
- [x] CHK010 CU-O102 — `test_destinos_populares_*` (3 tests, incluye la regresión del bug de abajo) + verificado en vivo con una búsqueda real.
- [x] CHK011 CU-O103 — `app/ofertas/tests/test_cupon.py` (9 tests: porcentaje, monto fijo, tope en 0 en vez de negativo, expirado, sin usos, doble canje, producto no aplicable, acumulación con/sin excepción) + verificado en vivo vía HTTP.
- [x] CHK012 CU-O104 — cubierto por CHK006.
- [x] CHK013 CU-O105 — cubierto por CHK002.

## Notas

- **Bug real #1 (PocketBase): un `json` requerido rechaza `{}` como "valor faltante" (400).** `campanas_email.segmento_criterio` es `json*` — pasar un diccionario vacío como default (sin criterio de segmento explícito) lo hace fallar, mismo gotcha ya documentado para `number`/`bool` requeridos en `0`/`false` (ver [[feedback_pocketbase_required_numerico]]). Corregido en `crear_campana()`: sin criterio explícito se guarda `{"segmento": "todos_los_suscriptores"}` en vez de `{}` — más correcto además de evitar el 400 (un criterio de verdad vacío no describe nada).
- **Bug real #2 (código propio): "Destinos populares" con origen INFERIDO (sin `?origen=` en la URL) nunca mostraba resultados, aunque el cálculo interno fuera correcto.** El router pasaba a la plantilla el query param crudo (vacío cuando el origen se infiere del historial del pasajero) en vez del origen que el servicio realmente usó — la plantilla decide qué bloque mostrar según esa variable. Encontrado verificando en vivo el camino de un pasajero real con historial de búsqueda (no solo el camino con `?origen=` explícito, que sí funcionaba y ocultaba el bug en los tests iniciales). `destinos_populares()` ahora retorna `(origen_usado, destinos)` en vez de solo la lista — test de regresión agregado (`test_destinos_populares_infiere_origen_del_historial_del_pasajero`).
- Al cerrar este módulo, actualizado `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
