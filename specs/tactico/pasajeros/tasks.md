# Tasks: Pasajeros (Táctico)

**Input:** [`plan.md`](./plan.md) · [`pasajeros-spec.md`](./pasajeros-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/pasajeros/` *(nivel Operativo ya implementado)*

---

## Fase 1: Ver segmentación (RF-PAS-T01)

**⚠️ Depende de `reserva_items` (Reservas, no implementado)** para datos reales — con datos de prueba sembrados manualmente se valida el mecanismo, no el caso real.

- [ ] T001 `app/pasajeros/router_segmentacion.py` — `GET /backoffice/pasajeros/segmentacion`, protegido por RBAC (CHK001)
- [ ] T002 Calcula frecuencia y destino preferido solo sobre reservas `confirmada` o posterior (CHK002, RN-PAS-T01)
- [ ] T003 Filtro instantáneo (REG-J9, CHK003)
- [ ] T004 [P] `app/pasajeros/tests/test_segmentacion.py`

---

## Fase 2: Exportar base (RF-PAS-T02)

- [ ] T005 `router_segmentacion.py` — `GET /backoffice/pasajeros/exportar`, genera CSV con campos acotados (CHK004, RN-PAS-T02)
- [ ] T006 [P] `app/pasajeros/tests/test_segmentacion.py` — exportación excluye campos sensibles (CHK004)

**Checkpoint:** un Administrador segmenta y exporta pasajeros con datos reales de reserva.

---

## Cierre

- [ ] T007 Correr `pytest app/pasajeros/` completo (Operativo + Táctico)
- [ ] T008 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 2 depende de Fase 1.
