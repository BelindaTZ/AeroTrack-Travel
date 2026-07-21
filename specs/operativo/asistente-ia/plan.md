# Plan de Implementación — Asistente IA

**Módulo:** Asistente IA
**Prefijo:** IA
**Spec:** [`asistente-ia-spec.md`](./asistente-ia-spec.md)
**Código fuente:** `app/asistente_ia/`
**Fecha:** 2026-07-18
**Estado:** ✅ Implementado 2026-07-19 — ver [`checklist.md`](./checklist.md). Sin credencial real de Groq/Gemini sembrada (bloqueo de infraestructura, no de código) — REG-H1 verificado igual, con el camino LLM fuera de la ecuación.

---

## Resumen

Conversación con IA (Groq/Gemini) para consultas informativas (sin sesión) y transaccionales sobre la propia reserva (con sesión), con contexto acotado y verificable (constitución H1) y escalación honesta a un agente humano cuando no puede resolver. Cubre 6 RF y 4 RN sobre 6 CU (CU-O106–O111). Dueño de `conversaciones_ia`, `mensajes_ia`.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2; cliente HTTP para Groq y/o Gemini (uso constante, generación en vivo). **Almacenamiento:** PocketBase — dueño de las 2 colecciones. **Restricciones:** REG-H1 es la restricción central de este módulo — toda respuesta con datos específicos debe verificarse contra el sistema en tiempo real, nunca generarse solo del conocimiento del modelo (RN-IA-001).

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-H1 (contexto de IA acotado y verificable) | Sí — **el principio central de este módulo** | RF-IA-003/004 consultan datos reales antes de responder; el prompt del sistema al LLM debe incluir instrucción explícita de no inventar y de citar solo lo verificado |
| REG-B3 (cero secretos hardcodeados) | Sí | API keys de Groq/Gemini en `configuracion_sistema`/env |
| REG-F1 (integración reemplazable) | Sí | Cliente LLM detrás de una interfaz propia — permite cambiar de Groq a Gemini o viceversa sin tocar el resto del módulo |
| REG-G1 (autoservicio) | Sí | Consulta informativa sin sesión; transaccional exige sesión pero sigue siendo autoservicio, no requiere agente |

Sin violaciones — no se llena Complexity Tracking, aunque REG-H1 exige diseño cuidadoso del prompt/orquestación (ver Fase 2).

---

## Estructura del proyecto

```text
app/asistente_ia/
├── __init__.py
├── router_conversacion.py   # RF-IA-001,002,005,006
├── schemas.py
├── services/
│   ├── llm_client.py          # cliente Groq/Gemini, aislado (REG-F1)
│   ├── contexto_service.py    # arma el contexto verificable (RN-IA-001): consulta datos reales antes de llamar al LLM
│   └── conversacion_service.py
├── repositories/
│   └── asistente_repo.py
├── templates/
│   └── (widget de chat flotante, ver diseno-visual.md v4)
└── tests/
    ├── test_conversacion.py
    ├── test_contexto_service.py   # verifica que no se inventan datos
    └── test_consulta_transaccional.py
```

**Decisión de estructura:** `contexto_service.py` es la pieza que hace cumplir REG-H1 — se ejecuta *antes* de llamar al LLM, recolecta los datos reales relevantes a la consulta (reserva del pasajero, requisitos de visa, etc.) y los inyecta como contexto acotado en el prompt; el LLM nunca responde "libre", siempre sobre ese contexto ya verificado.

---

## Fases de implementación

### Fase 1 — Conversación básica (RF-IA-001, 002, 005, 006)
**Precondición externa:** credenciales de Groq/Gemini sembradas.
**Entregable:** `router_conversacion.py`, `llm_client.py`, `conversacion_service.py`.

### Fase 2 — Consulta informativa con contexto verificable (RF-IA-003)
**Precondición externa:** Fase 1 completa; acceso de lectura a `requisitos_visa_cache` (Reservas) y catálogos relevantes.
**Entregable:** `contexto_service.py` (primera versión, alcance informativo).
**Nota crítica:** esta fase es donde se implementa REG-H1 — priorizar pruebas explícitas de que el asistente dice "no lo sé" cuando no hay dato verificable, en vez de aproximar.

### Fase 3 — Consulta transaccional (RF-IA-004)
**Precondición externa:** Fase 2 completa; Seguridad Fase 1 (sesión) y Reservas con datos reales.
**Entregable:** extiende `contexto_service.py` para incluir datos de reserva del pasajero autenticado, con verificación estricta de que solo accede a sus propios datos (RN-IA-002).

### Fase 4 — Escalación cuando no resuelve (RN-IA-003)
**Precondición externa:** `centro-ayuda-spec.md` (CU-O100) implementado.
**Entregable:** integración con el flujo de escalación existente.

---

## Complexity Tracking

*No aplica.*
