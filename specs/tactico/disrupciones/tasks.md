# Tasks: Disrupciones y Notificaciones (Táctico)

**Input:** [`plan.md`](./plan.md) · [`disrupciones-spec.md`](./disrupciones-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/disrupciones/` *(nivel Operativo ya implementado)*

---

## Fase 1: Dashboard de monitoreo (RF-DIS-T01)

- [ ] T001 `app/disrupciones/router_dashboard.py` — `GET /backoffice/disrupciones/dashboard`, protegido por RBAC Agente/Admin (CHK001)
- [ ] T002 [P] `app/disrupciones/tests/test_dashboard.py`

---

## Fase 2: Reporte de disrupciones (RF-DIS-T03)

- [ ] T003 `app/disrupciones/router_reporte.py` — `GET /backoffice/disrupciones/reporte`, agrupa por aerolínea/ruta (CHK002)
- [ ] T004 Filtro instantáneo (REG-J9, CHK003)
- [ ] T005 [P] `app/disrupciones/tests/test_reporte.py`

---

## Fase 3: Configurar umbral de risk score (RF-DIS-T02)

**⚠️ Sin efecto real hasta que CU-O83 (Operativo) exista** — implementar la UI de configuración, documentar explícitamente la dependencia.

- [ ] T006 `app/disrupciones/router_config_umbral.py` — `GET/POST /backoffice/disrupciones/config-umbral-riesgo` (CHK004)
- [ ] T007 Verificar que la alerta proactiva (cuando exista) nunca reemplaza la notificación reactiva de CU-O30 (CHK005, RN-DIS-T01)
- [ ] T008 [P] `app/disrupciones/tests/test_config_umbral.py`

**Checkpoint:** el umbral queda configurado, listo para cuando CU-O83 exista.

---

## Cierre

- [ ] T009 Correr `pytest app/disrupciones/` completo (Operativo + Táctico)
- [ ] T010 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Las 3 fases son independientes entre sí — Fase 3 depende de una pieza Operativa externa (CU-O83), no de otra fase de este nivel.
