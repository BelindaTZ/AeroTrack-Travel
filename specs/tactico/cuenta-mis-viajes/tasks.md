# Tasks: Cuenta de Usuario / Mis Viajes (Táctico)

**Input:** [`plan.md`](./plan.md) · [`cuenta-mis-viajes-spec.md`](./cuenta-mis-viajes-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/cuenta/` *(compartido con el nivel Operativo)*

---

## Fase 1: Configurar programa de beneficios (RF-CTA-T01, CU-T24)

- [ ] T001 Crear colección `programa_beneficios_niveles`
- [ ] T002 `app/cuenta/router_programa_beneficios.py` — `GET/POST /backoffice/cuenta/programa-beneficios`, protegido por RBAC (CHK001)
- [ ] T003 Valida que `puntos_minimos` no se solape con un nivel existente (CHK002, RN-CTA-T01)
- [ ] T004 [P] `app/cuenta/tests/test_programa_beneficios.py`

**Checkpoint:** un Administrador configura los niveles que consume `RF-CTA-006` (Operativo).

---

## Fase 2: Reporte de alertas de precio (RF-CTA-T02, CU-T25)

- [ ] T005 `app/cuenta/router_reporte_alertas.py` — `GET /backoffice/cuenta/reporte-alertas`, protegido por RBAC (CHK003)
- [ ] T006 Filtro instantáneo por período (REG-J9, CHK004)
- [ ] T007 Calcula conversión aproximada (reserva real posterior a la alerta, misma ruta), documenta la limitación de atribución en el propio reporte (CHK005, RN-CTA-T02)
- [ ] T008 [P] `app/cuenta/tests/test_reporte_alertas.py`

**Checkpoint:** un Administrador ve alertas activas y su tasa de conversión aproximada.

---

## Cierre

- [ ] T009 Correr `pytest app/cuenta/` completo (Operativo + Táctico)
- [ ] T010 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 1 es independiente de Fase 2 — priorizar Fase 1 porque bloquea a Operativo.
