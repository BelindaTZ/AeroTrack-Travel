# Tasks: Actividades (Táctico)

**Input:** [`plan.md`](./plan.md) · [`actividades-spec.md`](./actividades-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/actividades/` *(compartido con el nivel Operativo)*

---

## Fase 1: Configurar disponibilidad sintética (RF-ACT-T01, CU-T42)

**Nota de secuencia:** implementar junto con Operativo Fase 2 (`disponibilidad_service.py`), no después — RF-ACT-006 depende de esta configuración.

- [ ] T001 `app/actividades/router_config_disponibilidad.py` — `GET/POST /backoffice/actividades/config-disponibilidad`, protegido por `rbac_service` (CHK001)
- [ ] T002 Guarda en `configuracion_sistema` (categoría `disponibilidad_actividades`), global o por categoría, `modificado_por` obligatorio (CHK002)
- [ ] T003 Cambios no reescriben `actividades_horarios` ya generado (CHK003, RN-ACT-T01)
- [ ] T004 [P] `app/actividades/tests/test_config_disponibilidad.py` — guardar config (CHK002), no retroactivo (CHK003)

**Checkpoint:** un Administrador configura los parámetros que consume `disponibilidad_service.py` (Operativo).

---

## Fase 2: Reporte de actividades más reservadas (RF-ACT-T02, CU-T12)

**⚠️ Depende de `reserva_items` (Reservas, no implementado)**

- [ ] T005 `app/actividades/router_reporte.py` — `GET /backoffice/actividades/reporte`, protegido por RBAC (CHK004)
- [ ] T006 Filtro instantáneo por destino/categoría (REG-J9, CHK005)
- [ ] T007 Solo cuenta reservas `confirmada` o posterior (CHK006, RN-ACT-T02)
- [ ] T008 [P] `app/actividades/tests/test_reporte.py` — con datos de prueba sembrados manualmente, documentar dependencia de `reserva_items` real

**Checkpoint:** un Administrador ve el reporte — cierre completo solo con `reserva_items` real.

---

## Cierre

- [ ] T009 Correr `pytest app/actividades/` completo (Operativo + Táctico)
- [ ] T010 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 1 es independiente de Fase 2 — priorizar Fase 1 porque bloquea a Operativo.
