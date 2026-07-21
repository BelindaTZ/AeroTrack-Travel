# Especificación Operativa — Centro de Ayuda

**Módulo:** Centro de Ayuda
**Prefijo:** AYU
**Código fuente:** `app/centro_ayuda/` *(no existe todavía)*
**Casos de uso cubiertos:** CU-O97 (Buscar artículo de ayuda), CU-O98 (Ver artículo de ayuda), CU-O99 (Calificar utilidad de artículo o respuesta), CU-O100 (Escalar caso no resuelto a agente humano vía email)
**Actor:** Pasajero

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. **El centro de ayuda opera en primera instancia mediante el Asistente IA** (`asistente-ia-spec.md`, no redactado todavía) — este módulo es la base de conocimiento consultable directamente (búsqueda tradicional, sin IA) y el mecanismo de escalación cuando ni el artículo ni el asistente resuelven. **No existe chat en vivo con agente humano dentro de la aplicación** — el agente revisa y responde desde la bandeja de soporte real (Gmail API), no desde una UI de chat propia.

---

## Funcionalidad 1: Buscar y consultar artículos de ayuda (CU-O97, CU-O98)

### RF-AYU-001 — Buscar artículo de ayuda por categoría o término
El sistema debe permitir a un pasajero (autenticado o no) buscar artículos de ayuda activos (`articulos_ayuda.activo = true`) por categoría o término libre, mostrando resultados con título y categoría.

### RF-AYU-002 — Ver artículo de ayuda con contenido completo
El sistema debe mostrar el contenido completo de un artículo seleccionado, junto con la opción de calificar su utilidad (CU-O99).

---

## Funcionalidad 2: Calificar utilidad de artículo (CU-O99)

Extiende a CU-O98 — no es un CU independiente en el flujo.

### RF-AYU-003 — Calificar utilidad de artículo o respuesta
El sistema debe permitir calificar un artículo con pulgar arriba/abajo (`articulo_calificaciones.util`). La calificación anónima está permitida (`pasajero_id` nullable) — no se exige sesión para calificar un artículo público.

---

## Funcionalidad 3: Escalar caso no resuelto (CU-O100)

`<<extend>>` de Asistente IA (CU-O106–O108, `asistente-ia-spec.md`) — se dispara cuando ni la búsqueda de artículos ni el Asistente IA resuelven la consulta del pasajero.

### RF-AYU-004 — Escalar caso no resuelto a agente humano vía email
El sistema debe permitir a un pasajero autenticado escalar su caso, creando un registro en `casos_escalados` (asunto, mensaje, `estado = abierto`) y enviándolo por email real al equipo de soporte (Gmail API — mismo mecanismo de integración que Disrupciones usa para monitorear, aquí se usa para **enviar**). El hilo de correo real queda vinculado vía `gmail_thread_id` para que la respuesta del agente (`specs/tactico/centro-ayuda/`, CU-T36) se procese sobre la conversación real, no una simulación.

### RN-AYU-001 — Todo caso escalado requiere sesión activa
A diferencia de calificar un artículo (RN anónima permitida), escalar un caso exige que el pasajero esté autenticado — el sistema necesita saber a quién responder y asociar el caso a su cuenta.

---

## Reglas de negocio

- **RN-AYU-001** — *(Funcionalidad 3)* Escalar un caso requiere sesión activa, a diferencia de calificar un artículo.
- **RN-AYU-002** — Toda mutación de este módulo (calificación, escalación) se audita (CU-O41), salvo la calificación anónima, que audita sin `usuario_id` cuando no hay sesión.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /ayuda/buscar` | Categoría o término | HTML/JSON con artículos activos que coinciden |
| `GET /ayuda/{id}` | ID de artículo | HTML/JSON con contenido completo |
| `POST /ayuda/{id}/calificar` | Cookie JWT (opcional), pulgar arriba/abajo | Calificación registrada |
| `POST /ayuda/escalar` | Cookie JWT, asunto, mensaje | Caso creado + email real enviado al equipo de soporte |

---

## Historias de usuario

- **HU-AYU-01:** Como pasajero, quiero buscar artículos de ayuda por categoría o término, para resolver mi duda sin esperar respuesta de nadie.
- **HU-AYU-02:** Como pasajero, quiero ver el contenido completo de un artículo, para resolver mi consulta por mi cuenta.
- **HU-AYU-03:** Como pasajero, quiero calificar si un artículo me sirvió, para ayudar a mejorar el contenido futuro.
- **HU-AYU-04:** Como pasajero, quiero escalar mi caso a un agente humano cuando nada más resolvió mi duda, para no quedarme sin respuesta.

---

## Objetivo

Resolver la mayoría de las consultas del pasajero por autoservicio (artículo o Asistente IA), y garantizar una vía real de escalación a un humano cuando eso no alcanza — sin fingir un canal de chat en vivo que no existe.

---

## Escenarios

### Camino feliz
1. Un pasajero busca "qué pasa si mi vuelo se retrasa" (CU-O97) y encuentra un artículo relevante (CU-O98).
2. Lo califica como útil (CU-O99).

### Camino de escalación
1. Un pasajero no encuentra respuesta ni en artículos ni consultando al Asistente IA (`asistente-ia-spec.md`, CU-O106-108).
2. Escala su caso (CU-O100); se crea el registro y se envía el email real al equipo de soporte.
3. Un Agente lo atiende desde la bandeja de correo real (`specs/tactico/centro-ayuda/`, CU-T36), no desde una UI de chat.

### Manejo de errores
- **Búsqueda sin resultados:** mensaje claro, con acceso directo a escalar el caso.
- **Intento de escalar sin sesión:** se solicita iniciar sesión primero (RN-AYU-001).

---

## Criterios de aceptación

- **CU-O97:** Dado que existen artículos activos, cuando un pasajero busca por categoría o término, entonces ve los que coinciden.
- **CU-O98:** Dado que un pasajero selecciona un artículo, cuando accede a él, entonces ve su contenido completo.
- **CU-O99:** Dado que un pasajero (autenticado o no) califica un artículo, cuando confirma, entonces la calificación queda registrada.
- **CU-O100:** Dado que un pasajero autenticado escala un caso, cuando lo envía, entonces se crea el registro y se envía el email real al equipo de soporte, con el hilo de Gmail vinculado.

---

## Dependencias

- **Seguridad:** sesión (CU-O42, obligatoria solo para escalar); auditoría (CU-O41).
- **Asistente IA (`asistente-ia-spec.md`, no redactado todavía):** CU-O100 es `<<extend>>` de CU-O106-108 cuando el asistente no resuelve.
- **Este módulo, nivel Táctico (`specs/tactico/centro-ayuda/`):** CU-T28 gestiona los artículos que consume RF-AYU-001/002; CU-T36 gestiona la bandeja de casos escalados por RF-AYU-004.

---

## Casos de uso relacionados

- CU-O106–O108 (Asistente IA) — disparan CU-O100 cuando no resuelven.
- CU-T28 (Gestionar base de conocimiento, este módulo, Táctico) — dueño de los artículos.
- CU-T29 (Ver métricas de satisfacción, este módulo, Táctico) — consume CU-O99.
- CU-T36 (Gestionar bandeja de casos escalados, este módulo, Táctico) — consume CU-O100.

---

## Fuera de alcance

- Chat en vivo con agente humano dentro de la aplicación — explícitamente no existe en este catálogo; toda escalación es vía email.
- Respuesta automática del sistema a un caso escalado — la respuesta siempre la redacta un Agente humano desde la bandeja real (CU-T36).
