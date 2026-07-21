# Tasks: Autos (Táctico)

**Input:** [`plan.md`](./plan.md) · [`autos-spec.md`](./autos-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/autos/` *(compartido con el nivel Operativo)*

---

## Fase 0: Precondición

- [ ] T001 Confirmar que `app/autos/` (Operativo) existe con datos reales de catálogo.

---

## Fase 1: Reporte de reservas por proveedor y categoría (RF-AUT-T01, CU-T11)

**⚠️ Depende de `reserva_items` (Reservas, migración pendiente)** — con datos de prueba sembrados manualmente se valida el mecanismo, no el caso real de negocio; documentar la diferencia.

- [ ] T002 `app/autos/router_reporte.py` — `GET /backoffice/autos/reporte`, protegido por `rbac_service` (CHK001)
- [ ] T003 Agrupación por proveedor comercial/agregador y categoría de vehículo (CHK002)
- [ ] T004 Filtro instantáneo por rango de fechas (REG-J9, CHK003)
- [ ] T005 Solo cuenta reservas `confirmada` o posterior (CHK004, RN-AUT-T01)
- [ ] T006 [P] `app/autos/tests/test_reporte.py` — con datos de prueba sembrados manualmente (documentar dependencia de `reserva_items` real para cierre completo)

**Checkpoint:** un Administrador ve el reporte — cierre completo solo cuando `reserva_items` exista con datos reales.

---

## Cierre

- [ ] T007 Correr `pytest app/autos/` completo (Operativo + Táctico)
- [ ] T008 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md` cuando cierre

---

## Dependencias entre fases

- Fase 0 bloquea Fase 1.
