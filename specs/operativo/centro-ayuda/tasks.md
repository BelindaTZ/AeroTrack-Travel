# Tasks: Centro de Ayuda

**Input:** [`plan.md`](./plan.md) · [`centro-ayuda-spec.md`](./centro-ayuda-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/centro_ayuda/` *(no existe todavía)*

---

## Fase 0: Setup e infraestructura del módulo

- [ ] T001 Crear estructura `app/centro_ayuda/` (`__init__.py`, `services/`, `repositories/`, `templates/`, `tests/`)
- [ ] T002 [P] Crear colección `articulos_ayuda` — `scripts/pb_schema_centro_ayuda.py`
- [ ] T003 [P] Crear colección `articulo_calificaciones`
- [ ] T004 [P] Crear colección `casos_escalados`
- [ ] T005 Crear `app/centro_ayuda/repositories/ayuda_repo.py`
- [ ] T006 Crear `app/centro_ayuda/schemas.py`
- [ ] T007 [P] Sembrar artículos de prueba manualmente (mientras CU-T28 no exista)

**Checkpoint:** las 3 colecciones existen.

---

## Fase 1: Buscar y ver artículos (RF-AYU-001, 002)

- [ ] T008 `app/centro_ayuda/router_articulos.py` — `GET /ayuda/buscar` (CHK001)
- [ ] T009 `router_articulos.py` — `GET /ayuda/{id}` (CHK002)
- [ ] T010 [P] `app/centro_ayuda/templates/buscar_ayuda.html`, `articulo_ayuda.html`
- [ ] T011 [P] `app/centro_ayuda/tests/test_articulos.py` — búsqueda por categoría/término (CHK001), detalle completo (CHK002)

---

## Fase 2: Calificar artículo (RF-AYU-003)

- [ ] T012 `router_articulos.py` — `POST /ayuda/{id}/calificar`, `pasajero_id` nullable (CHK003)
- [ ] T013 [P] `app/centro_ayuda/tests/test_articulos.py` — calificación autenticada y anónima (CHK003)

**Checkpoint:** un pasajero busca, ve y califica artículos, con o sin sesión.

---

## Fase 3: Escalar caso (RF-AYU-004)

- [ ] T014 `app/centro_ayuda/services/escalacion_service.py` — reutiliza el cliente Gmail de Disrupciones para envío real (CHK004)
- [ ] T015 `app/centro_ayuda/router_escalacion.py` — `POST /ayuda/escalar`, exige sesión (CHK005, RN-AYU-001)
- [ ] T016 `escalacion_service.py` — vincula `gmail_thread_id` real del hilo enviado
- [ ] T017 [P] `app/centro_ayuda/tests/test_escalacion.py` — caso creado + email real enviado (CHK004), rechazo sin sesión (CHK005)

**Checkpoint:** un pasajero autenticado escala un caso y recibe confirmación real de envío.

---

## Cierre

- [ ] T018 Grep de verificación de cero secretos hardcodeados sobre `app/centro_ayuda/`
- [ ] T019 Correr suite completa `pytest app/centro_ayuda/` y re-correr los módulos existentes (en particular Disrupciones, por la integración Gmail compartida)
- [ ] T020 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 bloquea Fase 2.
- Fase 3 depende de la integración Gmail (reutilizada de Disrupciones) y de Seguridad Fase 1.
