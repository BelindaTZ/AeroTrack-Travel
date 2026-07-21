# Especificación Operativa — Asistente IA

**Módulo:** Asistente IA
**Prefijo:** IA
**Código fuente:** `app/asistente_ia/` *(no existe todavía)*
**Casos de uso cubiertos:** CU-O106 (Iniciar conversación), CU-O107 (Hacer consulta informativa de viaje), CU-O108 (Hacer consulta transaccional sobre reserva propia), CU-O109 (Ver historial de conversaciones), CU-O110 (Calificar respuesta del asistente), CU-O111 (Iniciar nueva conversación)
**Actor:** Pasajero (autenticado para CU-O108; el resto no exige sesión)

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. Fuente real: **Groq/Gemini** (uso constante — generación en vivo, no catálogo periódico), confirmado en `consideraciones.md` sección 7. **Gobernado por la constitución H1** (Contexto de IA acotado y verificable, `reglas.md` REG-H1): el asistente nunca inventa información de vuelos/tarifas/políticas — responde solo sobre datos que el sistema puede verificar, y respeta los permisos del usuario que lo invoca. Cuando no puede resolver, escala a un humano (`centro-ayuda-spec.md`, CU-O100), nunca improvisa una respuesta no verificable. Patrón de UI de referencia: chat flotante `bottom:0; right:24px` ya confirmado en el canvas de diseño v4 (`diseno-visual.md`).

---

## Funcionalidad 1: Iniciar y gestionar conversación (CU-O106, CU-O111)

### RF-IA-001 — Iniciar conversación con el Asistente IA
El sistema debe permitir a cualquier visitante (autenticado o no) iniciar una conversación (`conversaciones_ia`, `pasajero_id` — si no hay sesión, se documenta cómo se resuelve la identidad temporal, ver Fuera de alcance) y enviar mensajes que se registran en `mensajes_ia` con `rol` (pasajero/asistente).

### RF-IA-002 — Iniciar nueva conversación
El sistema debe permitir limpiar el contexto activo (iniciar una conversación nueva) sin perder el historial de conversaciones anteriores (CU-O109) — "limpiar contexto" es una acción sobre la conversación *activa* en curso, no una eliminación de datos.

---

## Funcionalidad 2: Consulta informativa (CU-O107)

### RF-IA-003 — Hacer consulta informativa de viaje
El sistema debe responder consultas informativas (documentos requeridos, destinos, clima, requisitos de viaje) usando el LLM configurado (Groq/Gemini), acotado a información que el sistema puede verificar contra sus propios datos (catálogos, `requisitos_visa_cache` de Reservas, etc. — REG-H1) — nunca inventando datos de vuelos, tarifas o políticas que no existan en el sistema.

### RN-IA-001 — Contexto acotado y verificable (constitución H1)
Toda respuesta del asistente que cite un dato específico (precio, política, disponibilidad) debe estar respaldada por una consulta real a los datos del sistema en el momento de responder, nunca generada solo del conocimiento general del modelo. Si el sistema no tiene el dato, el asistente lo dice explícitamente en vez de aproximar una respuesta plausible pero no verificada.

---

## Funcionalidad 3: Consulta transaccional (CU-O108)

### RF-IA-004 — Hacer consulta transaccional sobre reserva propia
El sistema debe permitir, solo a un pasajero con sesión activa (CU-O42), consultar al asistente sobre su propia reserva (estado, detalle, políticas aplicables) — el asistente consulta los datos reales de esa reserva específica del pasajero autenticado, respetando el alcance de sus propios datos (nunca los de otro pasajero, REG-H1 "respeta los permisos del usuario que la invoca").

### RN-IA-002 — Sin sesión activa, ninguna consulta transaccional procede
A diferencia de CU-O107 (informativa, sin sesión), CU-O108 exige sesión activa explícitamente — el asistente nunca expone datos de reserva sin autenticación verificada.

---

## Funcionalidad 4: Ver historial y calificar respuestas (CU-O109, CU-O110)

### RF-IA-005 — Ver historial de conversaciones anteriores
El sistema debe mostrar, a un pasajero autenticado, sus conversaciones anteriores (`conversaciones_ia.activa` no determina visibilidad en el historial — todas las conversaciones del pasajero son consultables, activas o no).

### RF-IA-006 — Calificar respuesta del asistente
El sistema debe permitir calificar con pulgar arriba/abajo cada mensaje de rol `asistente` (`mensajes_ia.calificacion`).

---

## Reglas de negocio

- **RN-IA-001** — *(Funcionalidad 2)* Contexto acotado y verificable (constitución H1) — sin dato real, sin respuesta inventada.
- **RN-IA-002** — *(Funcionalidad 3)* Consulta transaccional exige sesión activa, sin excepción.
- **RN-IA-003** — Si el asistente no puede resolver una consulta (informativa o transaccional) con datos verificables, ofrece escalar a un agente humano (`centro-ayuda-spec.md`, CU-O100) en vez de responder con información no verificada.
- **RN-IA-004** — Toda mutación de este módulo (crear conversación, calificar) se audita (CU-O41).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `POST /asistente/conversar` | Cookie JWT (opcional), mensaje | Respuesta del asistente + mensaje registrado en `mensajes_ia` |
| `POST /asistente/nueva-conversacion` | Cookie JWT (opcional) | Nueva conversación activa, historial anterior intacto |
| `GET /asistente/historial` | Cookie JWT | HTML/JSON con conversaciones anteriores del pasajero |
| `POST /asistente/mensajes/{id}/calificar` | Cookie JWT (opcional), pulgar arriba/abajo | Calificación registrada |

---

## Historias de usuario

- **HU-IA-01:** Como visitante, quiero iniciar una conversación con el asistente sin crear cuenta, para resolver dudas informativas rápido.
- **HU-IA-02:** Como pasajero, quiero preguntar sobre requisitos de viaje o clima del destino, para planificar sin buscar en varias páginas.
- **HU-IA-03:** Como pasajero autenticado, quiero preguntar sobre mi propia reserva, para resolver dudas puntuales sin buscar manualmente.
- **HU-IA-04:** Como pasajero, quiero ver mis conversaciones anteriores, para retomar contexto de algo que ya pregunté.
- **HU-IA-05:** Como pasajero, quiero calificar las respuestas del asistente, para ayudar a mejorar su calidad futura.
- **HU-IA-06:** Como pasajero, quiero iniciar una conversación nueva sin perder mi historial, para separar temas distintos.

---

## Objetivo

Resolver consultas informativas y transaccionales del pasajero con respuestas generadas por IA pero siempre ancladas a datos verificables del propio sistema — nunca inventadas — y ofrecer una vía de escalación humana honesta cuando el asistente no puede resolver.

---

## Escenarios

### Camino feliz (informativo)
1. Un visitante inicia una conversación (CU-O106) y pregunta sobre requisitos de visa para un destino (CU-O107).
2. El asistente consulta `requisitos_visa_cache`/Visa Requirement API en tiempo real y responde con el dato verificado.
3. El visitante califica la respuesta como útil (CU-O110).

### Camino feliz (transaccional)
1. Un pasajero autenticado pregunta "¿cuál es la política de cambio de mi reserva ABC123?" (CU-O108).
2. El asistente verifica que la reserva pertenece al pasajero autenticado, consulta su tarifa real y responde con la política verificada.

### Manejo de errores
- **Consulta transaccional sin sesión:** se rechaza, solicitando iniciar sesión (RN-IA-002).
- **Consulta que el sistema no puede verificar:** el asistente lo dice explícitamente y ofrece escalar a un agente (RN-IA-003), nunca inventa una respuesta plausible.

---

## Criterios de aceptación

- **CU-O106:** Dado que un visitante o pasajero envía un primer mensaje, cuando lo hace, entonces se crea una conversación y recibe respuesta.
- **CU-O107:** Dado que una consulta informativa tiene dato verificable en el sistema, cuando el asistente responde, entonces cita ese dato real; si no lo tiene, lo dice explícitamente.
- **CU-O108:** Dado que un pasajero autenticado pregunta sobre su propia reserva, cuando el asistente responde, entonces usa datos reales de esa reserva específica, nunca de otro pasajero.
- **CU-O109:** Dado que un pasajero tiene conversaciones anteriores, cuando consulta su historial, entonces las ve todas, activas o no.
- **CU-O110:** Dado que existe un mensaje del asistente, cuando el pasajero lo califica, entonces la calificación queda registrada.
- **CU-O111:** Dado que un pasajero tiene una conversación activa, cuando inicia una nueva, entonces el contexto se limpia sin perder el historial anterior.

---

## Dependencias

- **Seguridad:** sesión (CU-O42, obligatoria solo para CU-O108/O109); auditoría (CU-O41).
- **Reservas:** CU-O108 consulta datos reales de la reserva del pasajero autenticado.
- **Centro de Ayuda:** CU-O100 es el destino de escalación cuando este módulo no puede resolver (RN-IA-003).
- **Este módulo, nivel Táctico (`specs/tactico/asistente-ia/`):** CU-T34 configura tono/temas permitidos que condicionan las respuestas de RF-IA-003/004.

---

## Casos de uso relacionados

- CU-O81 (Consultar requisitos de visa, Reservas) — fuente de datos verificable para consultas informativas de destino.
- CU-O25 (Consultar estado de una reserva, Reservas) — fuente de datos verificable para consultas transaccionales.
- CU-O100 (Escalar caso, Centro de Ayuda) — destino cuando el asistente no resuelve.
- CU-T33 (Ver reporte de consultas frecuentes, este módulo, Táctico) — consume `mensajes_ia`.
- CU-T34 (Configurar el asistente IA, este módulo, Táctico) — condiciona el comportamiento de RF-IA-003/004.

---

## Fuera de alcance

- Identidad persistente de un visitante no autenticado entre sesiones distintas del navegador — sin cuenta, cada sesión de conversación se trata como nueva; no hay mecanismo de "recordar" a un visitante anónimo entre visitas.
- El asistente ejecutando acciones transaccionales (modificar/cancelar una reserva) — el catálogo de CU actual solo lo define como consulta, nunca como ejecutor de una mutación; cualquier cambio real lo hace el pasajero por el flujo normal del módulo correspondiente.
