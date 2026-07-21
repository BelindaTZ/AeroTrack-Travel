# Checklist de Validación: Disrupciones y Notificaciones (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Disrupciones cumple los RF/RN definidos en `disrupciones-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`disrupciones-spec.md`](./disrupciones-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-DIS-T01 — Dashboard accesible por rol Agente y Administrador.
- [ ] CHK002 RF-DIS-T03 — Reporte agrupa correctamente por aerolínea y ruta.
- [ ] CHK003 RF-DIS-T03 — Filtro de período se aplica sin botón "Aplicar".
- [ ] CHK004 RF-DIS-T02 — Umbral de risk score configurable (0-1).

## Reglas de negocio

- [ ] CHK005 RN-DIS-T01 — La alerta proactiva (cuando exista, dependiente de CU-O83) nunca reemplaza la notificación reactiva de CU-O30.
- [ ] CHK006 RN-DIS-T02 — Cambios de configuración quedan auditados.

## Trazabilidad de casos de uso

- [ ] CHK007 CU-T19 — prueba automatizada cubre el criterio de aceptación.
- [ ] CHK008 CU-T20 — ídem; **sin efecto real verificable hasta que CU-O83 (Operativo) exista** — la prueba puede validar que el umbral se guarda correctamente, no que dispara una alerta real todavía.
- [ ] CHK009 CU-T21 — ídem.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- CHK008 no debe cerrarse como "funcionalidad completa" sin CU-O83 real — documentar la limitación explícitamente si se cierra parcial.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
