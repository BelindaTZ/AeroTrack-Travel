# Tasks: Cuenta de Usuario / Mis Viajes

**Input:** [`plan.md`](./plan.md) · [`cuenta-mis-viajes-spec.md`](./cuenta-mis-viajes-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/cuenta/` — ✅ implementado 2026-07-19, ver `checklist.md` para el estado real ítem por ítem (esta lista de tareas queda como referencia histórica de planificación, no se marcó T### por T###).

---

## Fase 0: Setup e infraestructura del módulo

- [ ] T001 Crear estructura `app/cuenta/` (`__init__.py`, `services/`, `repositories/`, `templates/`, `tests/`)
- [ ] T002 [P] Crear colección `favoritos` — `scripts/pb_schema_cuenta.py`
- [ ] T003 [P] Crear colección `busquedas_recientes` (dueña técnica: este módulo la lee; la escritura la hace cada módulo de producto)
- [ ] T004 [P] Crear colección `viajes_personalizados`
- [ ] T005 [P] Crear colección `programa_beneficios_movimientos`
- [ ] T006 Crear `app/cuenta/repositories/cuenta_repo.py`
- [ ] T007 Crear `app/cuenta/schemas.py`

**Checkpoint:** las 4 colecciones existen.

---

## Fase 1: Ver Mis Viajes (RF-CTA-001)

**⚠️ Depende de `reserva_items` (Reservas, no implementado)**

- [ ] T008 `app/cuenta/router_mis_viajes.py` — `GET /mis-viajes`, agrupa por próxima/activa/pasada (CHK001)
- [ ] T009 [P] `app/cuenta/templates/mis_viajes.html`
- [ ] T010 [P] `app/cuenta/tests/test_mis_viajes.py`

---

## Fase 2: Favoritos y viajes personalizados (RF-CTA-002, 004)

- [ ] T011 `app/cuenta/router_favoritos.py` — `POST /favoritos`, `DELETE /favoritos/{id}` (CHK002)
- [ ] T012 `app/cuenta/router_viajes_personalizados.py` — `POST /viajes-personalizados` (CHK003)
- [ ] T013 [P] `app/cuenta/templates/favoritos.html`
- [ ] T014 [P] `app/cuenta/tests/test_favoritos.py`

**Checkpoint:** un pasajero guarda favoritos y crea viajes personalizados, sin depender de Reservas.

---

## Fase 3: Búsquedas recientes (RF-CTA-003)

**⚠️ Depende de que Vuelos/Hoteles/Autos/Actividades/Cruceros escriban en `busquedas_recientes`** — verificar si ya lo hacen al llegar a esta fase; si no, es trabajo cruzado en esos módulos, no solo en este.

- [ ] T015 `app/cuenta/router_busquedas.py` — `GET /mis-busquedas-recientes`, `POST /mis-busquedas-recientes/{id}/relanzar` (CHK004)
- [ ] T016 [P] `app/cuenta/tests/test_busquedas.py` — con datos de prueba sembrados si los módulos de producto no escriben todavía

---

## Fase 4: Programa de beneficios (RF-CTA-006)

- [ ] T017 `app/cuenta/router_puntos.py` — `GET /mi-cuenta/puntos`, calcula saldo excluyendo puntos vencidos según el nivel vigente (CHK005, RN-CTA-002)
- [ ] T018 Lee niveles de `programa_beneficios_niveles`; default documentado si `specs/tactico/cuenta-mis-viajes/` (CU-T24) no está implementado
- [ ] T019 [P] `app/cuenta/templates/mi_cuenta_puntos.html`
- [ ] T020 [P] `app/cuenta/tests/test_puntos.py` — saldo excluye vencidos (CHK005)

---

## Cierre

- [ ] T021 Correr suite completa `pytest app/cuenta/` y re-correr los módulos existentes
- [ ] T022 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 depende de `reserva_items` (bloqueante real).
- Fase 2 es independiente — implementable de inmediato.
- Fase 3 depende de retrofit en otros módulos.
- Fase 4 depende de `specs/tactico/cuenta-mis-viajes/` para el valor real (default sin eso).
