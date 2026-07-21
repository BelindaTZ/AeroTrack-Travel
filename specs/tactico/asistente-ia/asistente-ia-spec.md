# Especificación Táctica — Asistente IA

**Módulo:** Asistente IA
**Prefijo:** IA
**Código fuente:** `app/asistente_ia/` *(compartido con el nivel Operativo — ver `specs/operativo/asistente-ia/`)*
**Casos de uso cubiertos:** CU-T33 (Ver reporte de consultas frecuentes y temas sin respuesta), CU-T34 (Configurar el asistente IA)
**Actor:** Administrador

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. CU-T34 es **precondición real** de RF-IA-003/004 (Operativo, el tono y los temas permitidos condicionan cómo responde el asistente) — implementar junto con esa fase, no después.

---

## Funcionalidad 1: Configurar el asistente IA (CU-T34)

### RF-IA-T01 — Configurar el asistente IA
El sistema debe permitir a un Administrador configurar el tono de respuesta, los temas permitidos (para acotar el alcance de consulta, reforzando REG-H1 desde la configuración además del código) y respuestas predefinidas para accesos rápidos (preguntas frecuentes con respuesta fija, sin necesidad de generar una respuesta nueva del LLM cada vez). Los valores se guardan en `configuracion_sistema` (categoría `asistente_ia`).

### RN-IA-T01 — Los temas permitidos son una restricción, no una sugerencia
Si un tema no está en la lista de temas permitidos configurada, el asistente rechaza la consulta explícitamente (ofreciendo escalar si aplica) en vez de responder igual fuera de ese alcance — es una capa de control adicional sobre REG-H1, no solo una guía de estilo.

---

## Funcionalidad 2: Ver reporte de consultas frecuentes (CU-T33)

### RF-IA-T02 — Ver reporte de consultas frecuentes y temas sin respuesta
El sistema debe mostrar a un Administrador un reporte de los temas más consultados (agrupados desde `mensajes_ia` de rol `pasajero`) y los temas donde el asistente no pudo responder con dato verificable (RN-IA-001, Operativo) — este segundo grupo es la señal más directa de qué contenido nuevo agregar a la base de conocimiento (`centro-ayuda-spec.md`, CU-T28) o qué dato falta integrar al sistema.

---

## Reglas de negocio

- **RN-IA-T01** — *(Funcionalidad 1)* Los temas permitidos restringen activamente, no son solo una guía de estilo.
- **RN-IA-T02** — Los temas "sin respuesta" del reporte (CU-T33) son información accionable, no solo estadística — deben ser fácilmente exportables/consultables para alimentar la base de conocimiento.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET/POST /backoffice/asistente/configuracion` | Cookie JWT (Admin), tono, temas permitidos, respuestas predefinidas | Configuración guardada |
| `GET /backoffice/asistente/reporte` | Cookie JWT (Admin), filtro de período | HTML/JSON con consultas frecuentes y temas sin respuesta |

---

## Historias de usuario

- **HU-IA-T01:** Como administrador, quiero configurar el tono y los temas permitidos del asistente, para mantenerlo alineado con la marca y dentro de su alcance real.
- **HU-IA-T02:** Como administrador, quiero ver qué temas el asistente no pudo responder, para saber qué contenido agregar a la base de conocimiento.

---

## Objetivo

Dar al Administrador control sobre el comportamiento y alcance del asistente, y visibilidad directa de sus vacíos de conocimiento — cerrando el ciclo entre "el asistente no supo responder" y "se agrega el contenido que falta".

---

## Escenarios

### Camino feliz
1. Un Administrador configura el tono ("cercano y directo") y los temas permitidos (vuelos, pagos, disrupciones, documentos) (CU-T34).
2. Pasajeros conversan con el asistente (`specs/operativo/asistente-ia/`); algunas consultas quedan sin respuesta verificable.
3. El Administrador consulta el reporte (CU-T33), ve un tema recurrente sin respuesta, y crea un artículo de ayuda nuevo para cubrirlo.

### Manejo de errores
- **Consulta fuera de los temas permitidos:** el asistente la rechaza explícitamente, sin intentar responder igual (RN-IA-T01).

---

## Criterios de aceptación

- **CU-T34:** Dado que un Administrador configura tono/temas/respuestas predefinidas, cuando lo guarda, entonces el asistente (Operativo) usa esos valores en sus siguientes respuestas.
- **CU-T33:** Dado que existen mensajes de pasajero y respuestas sin dato verificable en el período, cuando un Administrador consulta el reporte, entonces ve ambos agrupados por tema.

---

## Dependencias

- **Asistente IA (Operativo):** RF-IA-003/004 son los consumidores reales de CU-T34; CU-T33 lee `mensajes_ia` que ese nivel genera.
- **Centro de Ayuda:** el reporte de CU-T33 informa directamente el trabajo de CU-T28 (gestión de base de conocimiento).
- **Seguridad:** RBAC (CU-O43), sesión (CU-O42).

---

## Casos de uso relacionados

- CU-O107, O108 (Consultas, Operativo) — consumidores de la configuración de CU-T34.
- CU-T28 (Gestionar base de conocimiento, Centro de Ayuda) — destino natural de los hallazgos de CU-T33.

---

## Fuera de alcance

- Entrenamiento o fine-tuning de un modelo propio — el módulo usa Groq/Gemini vía API, no entrena modelos.
- Configuración de temas permitidos por rol de pasajero (todos los pasajeros ven el mismo alcance configurado) — no está en el catálogo de CU actual.
