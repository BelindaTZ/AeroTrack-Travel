# Tasks: Facturación (Táctico)

**Input:** [`plan.md`](./plan.md) · [`facturacion-spec.md`](./facturacion-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/facturacion/` *(nivel Operativo ya implementado)*

---

## Fase 1: Dashboard financiero (RF-FAC-T01)

- [ ] T001 `app/facturacion/router_dashboard_financiero.py` — `GET /backoffice/facturacion/dashboard`, protegido por RBAC (CHK001)
- [ ] T002 Agrupa ingresos por `tipo_producto` (vía `comisiones`/`reserva_items`) (CHK002)
- [ ] T003 Muestra comisiones pendiente_cobro vs. cobrada, y remesas pendientes (CHK003)
- [ ] T004 [P] `app/facturacion/tests/test_dashboard_financiero.py`

---

## Fase 2: Reporte de ingresos (RF-FAC-T02)

- [ ] T005 `app/facturacion/router_reporte_ingresos.py` — `GET /backoffice/facturacion/reporte-ingresos`, protegido por RBAC (CHK004)
- [ ] T006 Filtro instantáneo por período/producto (REG-J9, CHK005)
- [ ] T007 Cargo de servicio y comisión se presentan como series separadas, nunca sumadas (CHK006, RN-FAC-T01)
- [ ] T008 [P] `app/facturacion/tests/test_reporte_ingresos.py`

**Checkpoint:** un Administrador ve el dashboard y genera reportes de ingresos con el desfase temporal respetado.

---

## Cierre

- [ ] T009 Correr `pytest app/facturacion/` completo (Operativo + Táctico)
- [ ] T010 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 2 depende de Fase 1.
