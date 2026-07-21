# Tasks: Centro de Ayuda (Táctico)

**Input:** [`plan.md`](./plan.md) · [`centro-ayuda-spec.md`](./centro-ayuda-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/centro_ayuda/` *(compartido con el nivel Operativo)*

---

## Fase 1: Gestionar base de conocimiento (RF-AYU-T01, CU-T28)

- [ ] T001 `app/centro_ayuda/router_gestion_articulos.py` — `GET/POST /backoffice/ayuda/articulos`, protegido por RBAC Administrador (CHK001)
- [ ] T002 Archivar en vez de eliminar físicamente (CHK002, RN-AYU-T01)
- [ ] T003 [P] `app/centro_ayuda/tests/test_gestion_articulos.py`

**Checkpoint:** un Administrador gestiona contenido real que consume la búsqueda del nivel Operativo.

---

## Fase 2: Gestionar bandeja de casos escalados (RF-AYU-T03, CU-T36)

**⚠️ Depende de casos escalados reales (Operativo Fase 3)**

- [ ] T004 `app/centro_ayuda/router_bandeja_casos.py` — `GET /backoffice/ayuda/casos`, protegido por RBAC **Agente** (verificar que no se restringe por error solo a Administrador — CU-T36 es de Agente) (CHK003)
- [ ] T005 `router_bandeja_casos.py` — `POST /backoffice/ayuda/casos/{id}/resolver`, conserva `gmail_thread_id` (CHK004, RN-AYU-T02)
- [ ] T006 [P] `app/centro_ayuda/templates/bandeja_casos.html`
- [ ] T007 [P] `app/centro_ayuda/tests/test_bandeja_casos.py` — acceso de Agente permitido (CHK003), resolver conserva el hilo (CHK004)

**Checkpoint:** un Agente gestiona la bandeja real de casos escalados.

---

## Fase 3: Métricas de satisfacción (RF-AYU-T02, CU-T29)

- [ ] T008 `app/centro_ayuda/router_metricas.py` — `GET /backoffice/ayuda/metricas`, protegido por RBAC Administrador (CHK005)
- [ ] T009 Filtro instantáneo por período (REG-J9, CHK006)
- [ ] T010 [P] `app/centro_ayuda/tests/test_metricas.py`

**Checkpoint:** un Administrador ve métricas reales de satisfacción y volumen de escalación.

---

## Cierre

- [ ] T011 Correr `pytest app/centro_ayuda/` completo (Operativo + Táctico)
- [ ] T012 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 1 es independiente — priorizar, alimenta a Operativo.
- Fase 2 depende de Operativo Fase 3 (casos reales).
- Fase 3 depende de Fase 1 y 2.
