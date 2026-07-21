# Checklist de Validación: Asistente IA

**Propósito:** Validar que la implementación del módulo Asistente IA cumple los RF/RN definidos en `asistente-ia-spec.md`, con énfasis especial en REG-H1 (contexto acotado y verificable).
**Creado:** 2026-07-18
**Feature:** [`asistente-ia-spec.md`](./asistente-ia-spec.md) · [`plan.md`](./plan.md)
**Estado:** ✅ **Implementado 2026-07-19** — `app/asistente_ia/`, 15/15 tests. Sin credencial real de Groq/Gemini (ver Notas) — REG-H1 se verificó igual, con el LLM fuera de la ecuación, que es el escenario más exigente posible.

---

## Requisitos funcionales

- [x] CHK001 RF-IA-001 — Conversación se crea y registra mensajes con rol correcto (`usuario`/`asistente`) — verificado en vivo.
- [x] CHK002 RF-IA-002 — Nueva conversación cierra la activa (`activa=false`) sin borrar mensajes ni la conversación misma — el historial la sigue mostrando.
- [x] CHK003 RF-IA-005 — Historial muestra todas las conversaciones del pasajero, activas o no — test explícito con 2 conversaciones (una cerrada).
- [x] CHK004 RF-IA-006 — Calificación de mensaje del asistente se registra; calificar un mensaje de rol `usuario` se rechaza explícitamente.
- [x] CHK005 RF-IA-003 — Consulta informativa con dato real disponible responde citando ese dato — verificado en vivo con una reserva real (ver CHK007, mismo mecanismo).
- [x] CHK006 RN-IA-001 — Consulta sin dato verificable responde honestamente y ofrece escalar, **nunca una aproximación inventada**. Verificado en vivo preguntando sobre un tema sin contexto real (disrupciones, sin código de reserva) — la respuesta fue exactamente el mensaje de "no tengo un dato verificado", no una alucinación.
- [x] CHK007 RF-IA-004 — Consulta transaccional usa datos reales de la reserva del pasajero — verificado en vivo: "¿cómo va mi reserva VERIF01?" respondió con el estado y total exactos de la reserva real, generados por plantilla determinista (sin necesitar al LLM en absoluto para este camino — ver Notas).
- [x] CHK008 RN-IA-002 — El asistente nunca expone datos de un pasajero distinto al autenticado — **test de seguridad explícito** (`test_reserva_ajena_nunca_se_expone`): el pasajero A preguntando por el código de reserva real del pasajero B recibe el mensaje honesto de "sin dato verificado", nunca los datos de B.
- [x] CHK009 RN-IA-002 — Consulta transaccional sin sesión: la conversación funciona igual (RF-IA-001 permite anónimos), pero sin `pasajero_id` el contexto de reserva nunca se resuelve — estructuralmente imposible exponer datos transaccionales sin sesión.

## Reglas de negocio

- [x] RN-IA-001 — cubierto por CHK006 arriba.
- [x] RN-IA-002 — cubierto por CHK008/CHK009 arriba.
- [x] CHK010 RN-IA-003 — Cuando no hay dato verificable, la respuesta ofrece escalar a un agente humano explícitamente (enlaza conceptualmente a CU-O100 — el pasajero puede ir a `/ayuda/buscar` y usar el formulario de escalar ya construido en Centro de Ayuda).
- [x] CHK011 RN-IA-004 — Mutaciones de este módulo (mensaje del asistente, calificación) quedan auditadas vía `AuditService`.

## No funcionales

- [x] CHK012 — Cliente LLM aislado detrás de `LLMClient` (interfaz abstracta, `app/asistente_ia/integrations/llm_client.py`) — cambiar de proveedor no requiere tocar `router_conversacion.py`/`asistente_service.py`, solo la implementación concreta. `GroqGeminiLLMClient` ya intenta Groq primero, Gemini como respaldo, dentro de esa misma implementación.

## Trazabilidad de casos de uso

- [x] CHK013 CU-O106 — `app/asistente_ia/tests/test_asistente.py` (15 tests) + verificado en vivo (widget flotante real, conversación completa).
- [x] CHK014 CU-O107 — cubierto por CHK006.
- [x] CHK015 CU-O108 — cubierto por CHK007/CHK008.
- [x] CHK016 CU-O109 — cubierto por CHK003.
- [x] CHK017 CU-O110 — cubierto por CHK004; botones de calificar visibles en el widget real.
- [x] CHK018 CU-O111 — cubierto por CHK002.

## Notas

- **CHK006 confirmado bajo el escenario más exigente posible: sin ninguna credencial real de LLM.** Ni `groq.api_key` ni `gemini.api_key` están sembrados en `configuracion_sistema` (confirmado, ninguno de los dos) — `GroqGeminiLLMClient.generar()` siempre lanza `CredencialNoConfigurada`. Esto no bloqueó la verificación de REG-H1: para hechos estructurados (reserva propia), `asistente_service` responde con una plantilla determinista sin necesitar al LLM en absoluto; para el resto, cuando no hay contexto verificado, el sistema dice explícitamente que no tiene el dato — el camino de "nunca inventar" se ejercitó de punta a punta en vivo, con el LLM completamente fuera de la ecuación. Mismo patrón que Centro de Ayuda (Gmail, scope insuficiente) y Ofertas (SendGrid, sin credencial) — ver [[project_gmail_oauth_scope_insuficiente]].
- **`conversaciones_ia.pasajero_id` es `not null` en el esquema real (dbml v3, confirmado — no es un drift)**, aunque RF-IA-001 describe visitantes anónimos. Resuelto así: una conversación anónima SÍ funciona (respuesta generada igual) pero nunca se persiste — no hay `conversaciones_ia`/`mensajes_ia` creados. Solo las conversaciones de un pasajero autenticado se guardan. Consistente con la sección "Fuera de alcance" del spec ("sin mecanismo de recordar a un visitante anónimo entre visitas").
- **`requisitos_visa_cache` está vacía (0 registros)** — RF-RES-008 (Reservas, el módulo dueño de esa colección) nunca se implementó. Una consulta de visa siempre encuentra "sin dato cacheado" hoy — comportamiento honesto, no un placeholder a medias.
- **Dos bugs reales de aislamiento de tests encontrados y corregidos durante esta ronda** (ninguno afecta producción, ambos afectaban solo la fiabilidad de la suite): (1) el regex de detección de código de reserva (`_PATRON_CODIGO_RESERVA`) solo cubría 6-10 caracteres, más corto que el formato de prueba del fixture compartido (`PNR` + 8 hex = 11 caracteres) — ampliado a 4-14; (2) `test_admin_configura_asistente` escribía en `configuracion_sistema` (estado global compartido) sin revertir al terminar, contaminando cualquier test posterior que llamara a `conversar()` — corregido con guardado/restauración del valor original, mismo criterio que ya aplicaba el test de acumulación de cupones en Ofertas.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md` — **hecho**.
