# Checklist de Validación: Cruceros (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Cruceros cumple los RF/RN definidos en `cruceros-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`cruceros-spec.md`](./cruceros-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-CRU-T01 — Configuración protegida por RBAC (solo Administrador).
- [ ] CHK002 RF-CRU-T01 — Se guarda en `configuracion_sistema` con `modificado_por` obligatorio, global o por tipo de camarote.
- [ ] CHK003 RN-CRU-T01 — Un cambio de configuración no reescribe cupos ya generados.
- [ ] CHK004 RF-CRU-T02 — Reporte protegido por RBAC.
- [ ] CHK005 RF-CRU-T02 — Filtros de destino/temporada se aplican sin botón "Aplicar".
- [ ] CHK006 RN-CRU-T02 — El conteo refleja consultas/interés (búsquedas + vistas de detalle), no solo reservas confirmadas — verificar que no se implementó por error como "solo reservas", homologando incorrectamente con otros módulos.

## Trazabilidad de casos de uso

- [ ] CHK007 CU-T43 — prueba automatizada cubre el criterio de aceptación; verificar además que `specs/operativo/cruceros/` (RF-CRU-006) efectivamente lee estos valores una vez implementado.
- [ ] CHK008 CU-T13 — prueba cubre el criterio de aceptación, incluyendo el mecanismo de registro de consultas decidido en `tasks.md` T005.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- CHK007 no cierra completo hasta confirmar la integración real con `disponibilidad_service.py` del nivel Operativo.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
