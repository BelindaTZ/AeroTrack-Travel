# Tasks: Cruceros (Táctico)

**Input:** [`plan.md`](./plan.md) · [`cruceros-spec.md`](./cruceros-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/cruceros/` *(compartido con el nivel Operativo)*

---

## Fase 1: Configurar disponibilidad sintética de camarotes (RF-CRU-T01, CU-T43)

**Nota de secuencia:** implementar junto con Operativo Fase 2 (`disponibilidad_service.py`), no después.

- [ ] T001 `app/cruceros/router_config_disponibilidad.py` — `GET/POST /backoffice/cruceros/config-disponibilidad`, protegido por `rbac_service` (CHK001)
- [ ] T002 Guarda en `configuracion_sistema` (categoría `disponibilidad_cruceros`), global o por tipo de camarote, `modificado_por` obligatorio (CHK002)
- [ ] T003 Cambios no reescriben `cruceros_camarotes_tarifa.cupos_disponibles` ya generado (CHK003, RN-CRU-T01)
- [ ] T004 [P] `app/cruceros/tests/test_config_disponibilidad.py`

**Checkpoint:** un Administrador configura los parámetros que consume `disponibilidad_service.py` (Operativo).

---

## Fase 2: Reporte de cruceros más consultados (RF-CRU-T02, CU-T13)

**⚠️ Requiere decidir primero el mecanismo de registro de consultas** (ver `plan.md` — no hay un log dedicado en el dbml actual; evaluar antes de codificar).

- [ ] T005 Decidir e implementar el mecanismo de registro de consultas (búsquedas CU-O71 + vistas de detalle CU-O72/O74) — nueva colección liviana o campo contador, documentar la decisión en `cruceros-spec.md` cuando se tome
- [ ] T006 `app/cruceros/router_reporte.py` — `GET /backoffice/cruceros/reporte`, protegido por RBAC (CHK004)
- [ ] T007 Filtro instantáneo por destino/temporada (REG-J9, CHK005)
- [ ] T008 El conteo refleja consultas/interés, no solo reservas confirmadas (CHK006, RN-CRU-T02)
- [ ] T009 [P] `app/cruceros/tests/test_reporte.py`

**Checkpoint:** un Administrador ve el reporte de interés por crucero.

---

## Cierre

- [ ] T010 Correr `pytest app/cruceros/` completo (Operativo + Táctico)
- [ ] T011 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 1 es independiente de Fase 2 — priorizar Fase 1 porque bloquea a Operativo.
- Fase 2 depende de la decisión de mecanismo de registro (T005) antes de cualquier otra tarea de esa fase.
