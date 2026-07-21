# Tasks: Asistente IA (Táctico)

**Input:** [`plan.md`](./plan.md) · [`asistente-ia-spec.md`](./asistente-ia-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/asistente_ia/` *(compartido con el nivel Operativo)*

---

## Fase 1: Configurar el asistente (RF-IA-T01, CU-T34)

- [ ] T001 `app/asistente_ia/router_config_asistente.py` — `GET/POST /backoffice/asistente/configuracion`, protegido por RBAC (CHK001)
- [ ] T002 Guarda tono, temas permitidos, respuestas predefinidas en `configuracion_sistema` (categoría `asistente_ia`) (CHK002)
- [ ] T003 `contexto_service.py` (Operativo) lee temas permitidos y rechaza consultas fuera de alcance explícitamente (CHK003, RN-IA-T01)
- [ ] T004 [P] `app/asistente_ia/tests/test_config_asistente.py` — tema fuera de alcance rechazado (CHK003)

**Checkpoint:** un Administrador configura el comportamiento real del asistente Operativo.

---

## Fase 2: Reporte de consultas frecuentes (RF-IA-T02, CU-T33)

- [ ] T005 `app/asistente_ia/router_reporte_asistente.py` — `GET /backoffice/asistente/reporte`, protegido por RBAC (CHK004)
- [ ] T006 Filtro instantáneo por período (REG-J9, CHK005)
- [ ] T007 Agrupa por tema, separando consultas resueltas de las sin dato verificable (CHK006)
- [ ] T008 [P] `app/asistente_ia/tests/test_reporte_asistente.py`

**Checkpoint:** un Administrador ve qué temas necesitan contenido nuevo en la base de conocimiento.

---

## Cierre

- [ ] T009 Correr `pytest app/asistente_ia/` completo (Operativo + Táctico)
- [ ] T010 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 1 es independiente — priorizar, condiciona a Operativo desde el inicio (RN-IA-T01).
- Fase 2 depende de datos reales de `mensajes_ia`.
