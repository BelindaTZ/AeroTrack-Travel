# Tasks: Asistente IA

**Input:** [`plan.md`](./plan.md) · [`asistente-ia-spec.md`](./asistente-ia-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/asistente_ia/` *(no existe todavía)*

---

## Fase 0: Setup e infraestructura del módulo

- [ ] T001 Crear estructura `app/asistente_ia/` (`__init__.py`, `services/`, `repositories/`, `templates/`, `tests/`)
- [ ] T002 [P] Crear colección `conversaciones_ia` — `scripts/pb_schema_asistente_ia.py`
- [ ] T003 [P] Crear colección `mensajes_ia`
- [ ] T004 Crear `app/asistente_ia/repositories/asistente_repo.py`
- [ ] T005 Crear `app/asistente_ia/schemas.py`
- [ ] T006 [P] Sembrar credenciales de Groq/Gemini en `configuracion_sistema`

**Checkpoint:** las 2 colecciones existen.

---

## Fase 1: Conversación básica (RF-IA-001, 002, 005, 006)

- [ ] T007 `app/asistente_ia/services/llm_client.py` — cliente aislado de Groq/Gemini (REG-F1)
- [ ] T008 `app/asistente_ia/services/conversacion_service.py` — crea/gestiona conversación, registra mensajes (CHK001)
- [ ] T009 `app/asistente_ia/router_conversacion.py` — `POST /asistente/conversar`, `POST /asistente/nueva-conversacion` (CHK002)
- [ ] T010 `router_conversacion.py` — `GET /asistente/historial`, `POST /asistente/mensajes/{id}/calificar` (CHK003, CHK004)
- [ ] T011 [P] Widget de chat flotante (design system v4, patrón ya confirmado en el canvas de diseño)
- [ ] T012 [P] `app/asistente_ia/tests/test_conversacion.py` — conversación con/sin sesión (CHK001), nueva conversación preserva historial (CHK002)

---

## Fase 2: Consulta informativa con contexto verificable (RF-IA-003)

**⚠️ Fase crítica para REG-H1 — priorizar pruebas de "no invención" sobre pruebas de "respuesta correcta".**

- [ ] T013 `app/asistente_ia/services/contexto_service.py` — recolecta datos reales (requisitos de visa, catálogos) antes de construir el prompt (CHK005)
- [ ] T014 Prompt del sistema al LLM incluye instrucción explícita de no inventar y de decir "no lo sé" sin dato verificable (CHK006, RN-IA-001)
- [ ] T015 [P] `app/asistente_ia/tests/test_contexto_service.py` — consulta con dato real disponible responde con ese dato (CHK005); consulta sin dato disponible responde "no lo sé", nunca una aproximación plausible (CHK006) — **este segundo caso es el más importante de probar de todo el módulo**

---

## Fase 3: Consulta transaccional (RF-IA-004)

- [ ] T016 `contexto_service.py` — extiende para incluir datos de reserva del pasajero autenticado (CHK007)
- [ ] T017 Verifica que la reserva consultada pertenece al pasajero autenticado antes de incluirla en el contexto — nunca datos de otro pasajero (CHK008, RN-IA-002)
- [ ] T018 Rechaza consulta transaccional sin sesión activa (CHK009, RN-IA-002)
- [ ] T019 [P] `app/asistente_ia/tests/test_consulta_transaccional.py` — datos propios sí, datos de otro pasajero no (CHK008), sin sesión se rechaza (CHK009)

---

## Fase 4: Escalación cuando no resuelve (RN-IA-003)

**⚠️ Depende de `centro-ayuda-spec.md` (CU-O100) implementado**

- [ ] T020 `contexto_service.py`/`conversacion_service.py` — cuando no hay dato verificable, ofrece explícitamente la opción de escalar (llama a `POST /ayuda/escalar` de Centro de Ayuda)
- [ ] T021 [P] `app/asistente_ia/tests/test_conversacion.py` — oferta de escalación cuando no hay dato verificable

---

## Cierre

- [ ] T022 Grep de verificación de cero secretos hardcodeados sobre `app/asistente_ia/`
- [ ] T023 Correr suite completa `pytest app/asistente_ia/` y re-correr los módulos existentes
- [ ] T024 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 bloquea Fase 2.
- Fase 3 depende de Fase 2 y de Seguridad Fase 1.
- Fase 4 depende de Centro de Ayuda implementado.
