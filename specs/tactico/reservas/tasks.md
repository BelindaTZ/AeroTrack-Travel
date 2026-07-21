# Tasks: Reservas (Táctico)

**Input:** [`plan.md`](./plan.md) · [`reservas-spec.md`](./reservas-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/reservas/` *(nivel Operativo ya implementado)*

---

## Fase 1: Reporte por estado (RF-RES-T01)

- [ ] T001 `app/reservas/router_reporte_estado.py` — `GET /backoffice/reservas/reporte-estado`, protegido por RBAC Administrador (CHK001)
- [ ] T002 Filtro instantáneo por período (REG-J9, CHK002)
- [ ] T003 [P] `app/reservas/tests/test_reporte_estado.py`

---

## Fase 2: Monitorear próximas a vencer (RF-RES-T02)

- [ ] T004 `app/reservas/router_proximas_vencer.py` — `GET /backoffice/reservas/proximas-vencer`, protegido por RBAC **Agente o Administrador** (verificar que no se restringe solo a Admin) (CHK003)
- [ ] T005 No introduce ninguna acción de extensión de plazo (CHK004, RN-RES-T01)
- [ ] T006 [P] `app/reservas/tests/test_proximas_vencer.py`

---

## Fase 3: Configurar políticas de reembolso (RF-RES-T03)

- [ ] T007 `app/reservas/router_politicas.py` — `GET/POST /backoffice/reservas/politicas-reembolso`, protegido por RBAC Administrador (CHK005)
- [ ] T008 Formulario incluye selección de `tipo_producto` (vuelo/hotel/auto/actividad/crucero) (CHK006)
- [ ] T009 [P] `app/reservas/tests/test_politicas.py` — política nueva es referenciable por cada vertical

**Checkpoint:** un Administrador gestiona políticas de reembolso reales para las 5 verticales de producto.

---

## Cierre

- [ ] T010 Correr `pytest app/reservas/` completo (Operativo + Táctico) — confirmar cero regresión sobre los 21 tests ya existentes
- [ ] T011 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Las 3 fases son independientes entre sí.
