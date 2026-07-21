# Checklist de Validación: Vuelos (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Vuelos cumple los RF/RN definidos en `vuelos-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`vuelos-spec.md`](./vuelos-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-VUE-T01 — Configuración de catálogo protegida por RBAC.
- [ ] CHK002 RF-VUE-T02 — Estado del DAG muestra alerta visual ante corrida fallida.
- [ ] CHK003 RF-VUE-T03 — Reporte de rutas protegido por RBAC.
- [ ] CHK004 RN-VUE-T02 — Conversión calculada solo con datos reales de búsqueda y reserva, nunca aproximada.
- [ ] CHK005 RF-VUE-T04 — Recargo/proporción de asientos premium configurable por tipo de avión.
- [ ] CHK006 RF-VUE-T05 — Ventana de check-in gratuito configurable en horas.
- [ ] CHK007 RF-VUE-T06 — Rotación de clase de cabina configurable.

## Reglas de negocio

- [ ] CHK008 RN-VUE-T01 — CU-T07 reutiliza `sincronizaciones_log` (Integraciones) en vez de un log paralelo, cuando ese módulo ya existe.
- [ ] CHK009 RN-VUE-T03 — Verificar que `specs/operativo/vuelos/` (RF-VUE-010/012/013) efectivamente lee estos 3 valores en vez de un default hardcodeado, una vez ambos niveles estén implementados.

## Trazabilidad de casos de uso

- [ ] CHK010 CU-T06 — prueba automatizada cubre el criterio de aceptación.
- [ ] CHK011 CU-T07 — ídem.
- [ ] CHK012 CU-T08 — ídem; bloqueado hasta el retrofit de `busquedas_recientes` y `reserva_items`.
- [ ] CHK013 CU-T39 — ídem.
- [ ] CHK014 CU-T40 — ídem.
- [ ] CHK015 CU-T41 — ídem.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- CHK009 es el ítem de mayor valor real de este checklist — confirma que la Fase 3 de este nivel realmente desbloqueó la Fase 9 de Vuelos Operativo, no solo que los valores se guardan sin usarse.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
