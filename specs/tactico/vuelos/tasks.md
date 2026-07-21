# Tasks: Vuelos (Táctico)

**Input:** [`plan.md`](./plan.md) · [`vuelos-spec.md`](./vuelos-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/vuelos/` *(nivel Operativo ya implementado)*

---

## Fase 1: Configurar y monitorear catálogo (RF-VUE-T01, T02)

- [ ] T001 `app/vuelos/router_config_catalogo.py` — `GET/POST /backoffice/vuelos/config-catalogo`, protegido por RBAC (CHK001)
- [ ] T002 `router_config_catalogo.py` — `GET /backoffice/vuelos/estado-dag`, lee últimas corridas (reutiliza `sincronizaciones_log` si Integraciones ya existe) (CHK002, RN-VUE-T01)
- [ ] T003 [P] `app/vuelos/tests/test_config_catalogo.py`

---

## Fase 2: Reporte de rutas (RF-VUE-T03)

**⚠️ Depende del retrofit de `busquedas_recientes` y de `reserva_items` (ninguno implementado)**

- [ ] T004 `app/vuelos/router_reporte_rutas.py` — `GET /backoffice/vuelos/reporte-rutas`, protegido por RBAC (CHK003)
- [ ] T005 Calcula conversión relacionando búsquedas y reservas reales, nunca aproximada (CHK004, RN-VUE-T02)
- [ ] T006 [P] `app/vuelos/tests/test_reporte_rutas.py` — con datos de prueba sembrados, documentar dependencia real

---

## Fase 3: Configuración de asientos/cabina (RF-VUE-T04, T05, T06)

**⚠️ Prioridad alta — desbloquea Vuelos Operativo Fase 9 (CU-O114–O117)**

- [ ] T007 `app/vuelos/router_config_asientos.py` — `GET/POST /backoffice/vuelos/config-asientos`, recargo/proporción por tipo de avión (CHK005)
- [ ] T008 `router_config_asientos.py` — `GET/POST /backoffice/vuelos/config-checkin`, horas antes del vuelo (CHK006)
- [ ] T009 `router_config_asientos.py` — `GET/POST /backoffice/vuelos/config-rotacion-cabina` (CHK007)
- [ ] T010 [P] `app/vuelos/tests/test_config_asientos.py`

**Checkpoint:** las 3 configuraciones quedan listas para que Vuelos Operativo Fase 9 las consuma en vez de un default hardcodeado.

---

## Cierre

- [ ] T011 Correr `pytest app/vuelos/` completo (Operativo + Táctico) — confirmar cero regresión sobre los 20 tests ya existentes
- [ ] T012 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Las 3 fases son independientes entre sí.
- Fase 3 es la de mayor prioridad real por desbloquear trabajo Operativo pendiente.
