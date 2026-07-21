# Tasks: Paquetes (Táctico)

**Input:** [`plan.md`](./plan.md) · [`paquetes-spec.md`](./paquetes-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/paquetes/` *(compartido con el nivel Operativo)*

---

## Fase 1: Configurar porcentajes de descuento (RF-PAQ-T01, CU-T14)

**Nota de secuencia:** implementar junto con Operativo Fase 2, no después.

- [ ] T001 `app/paquetes/router_tipos_descuento.py` — `GET/POST /backoffice/paquetes/tipos-descuento`, protegido por RBAC (CHK001)
- [ ] T002 Crea/edita combinación con `combinacion` (texto libre controlado por UI), `porcentaje_descuento`, `activo` (CHK002)
- [ ] T003 Desactivar/editar no afecta paquetes ya confirmados (CHK003, RN-PAQ-T01)
- [ ] T004 [P] `app/paquetes/tests/test_tipos_descuento.py`

**Checkpoint:** un Administrador configura las combinaciones que consume `paquete_service.py` (Operativo).

---

## Fase 2: Reporte de combinaciones más vendidas (RF-PAQ-T02, CU-T15)

**⚠️ Depende de `reserva_items`/`reservas.es_paquete` (Reservas, no implementado)**

- [ ] T005 `app/paquetes/router_reporte.py` — `GET /backoffice/paquetes/reporte`, protegido por RBAC (CHK004)
- [ ] T006 Filtro instantáneo por período (REG-J9, CHK005)
- [ ] T007 Solo cuenta paquetes `confirmada` o posterior; calcula margen como `sum(reserva_items.precio_final) − reservas.total_pagar` (costo del descuento, no rentabilidad neta — ver RF-PAQ-T02) (CHK006, RN-PAQ-T02)
- [ ] T008 [P] `app/paquetes/tests/test_reporte.py` — con datos de prueba sembrados manualmente, documentar dependencia real

**Checkpoint:** un Administrador ve el reporte — cierre completo solo con datos reales.

---

## Cierre

- [ ] T009 Correr `pytest app/paquetes/` completo (Operativo + Táctico)
- [ ] T010 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 1 es independiente de Fase 2 — priorizar Fase 1 porque bloquea a Operativo.
