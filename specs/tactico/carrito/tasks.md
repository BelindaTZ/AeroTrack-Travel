# Tasks: Carrito (Táctico)

**Input:** [`plan.md`](./plan.md) · [`carrito-spec.md`](./carrito-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/carrito/` *(compartido con el nivel Operativo)*

---

## Fase 1: Configurar y detectar abandono (RF-CAR-T01, CU-T26)

- [ ] T001 `app/carrito/router_config_abandono.py` — `GET/POST /backoffice/carrito/config-abandono`, protegido por RBAC (CHK001)
- [ ] T002 Guarda umbral de inactividad y plantilla en `configuracion_sistema` (categoría `carrito_abandonado`) (CHK002)
- [ ] T003 Job programado — marca `carritos.estado = abandonado` cuando supera el umbral sin actividad, dispara email vía la capa de envío ya existente (CHK003)
- [ ] T004 Solo carritos `activo` pueden marcarse `abandonado`; `convertido` nunca cambia (CHK004, RN-CAR-T01)
- [ ] T005 [P] `app/carrito/tests/test_config_abandono.py` — detección de abandono (CHK003), carrito convertido nunca se marca (CHK004)

**Checkpoint:** carritos inactivos se marcan abandonados y reciben el recordatorio configurado.

---

## Fase 2: Reporte de recuperación (RF-CAR-T02, CU-T27)

- [ ] T006 `app/carrito/router_reporte.py` — `GET /backoffice/carrito/reporte`, protegido por RBAC (CHK005)
- [ ] T007 Filtro instantáneo por período (REG-J9, CHK006)
- [ ] T008 Calcula tasa de recuperación: abandonado → activo → convertido cuenta como recuperado (CHK007, RN-CAR-T02)
- [ ] T009 [P] `app/carrito/tests/test_reporte.py` — carrito recuperado vs. no recuperado (CHK007)

**Checkpoint:** un Administrador ve la tasa de recuperación real de carritos abandonados.

---

## Cierre

- [ ] T010 Correr `pytest app/carrito/` completo (Operativo + Táctico)
- [ ] T011 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 1 bloquea Fase 2 (necesita carritos abandonados reales).
