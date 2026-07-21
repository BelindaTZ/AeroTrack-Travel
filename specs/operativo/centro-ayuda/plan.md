# Plan de Implementación — Centro de Ayuda

**Módulo:** Centro de Ayuda
**Prefijo:** AYU
**Spec:** [`centro-ayuda-spec.md`](./centro-ayuda-spec.md)
**Código fuente:** `app/centro_ayuda/`
**Fecha:** 2026-07-18
**Estado:** ✅ Implementado 2026-07-19 (20 tests). Envío real de email bloqueado por un problema de scope OAuth preexistente — ver `checklist.md`.

---

## Resumen

Base de conocimiento de autoservicio (búsqueda + artículo + calificación) y escalación real por email cuando el autoservicio no resuelve. Cubre 4 RF y 2 RN sobre 4 CU (CU-O97–O100). Dueño de `articulos_ayuda`, `articulo_calificaciones`, `casos_escalados`.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2; Gmail API (OAuth) para envío real de casos escalados — **mismas credenciales que Disrupciones** (REG-B3, REG-I6), reutilizar la integración existente, no crear una segunda conexión OAuth separada. **Almacenamiento:** PocketBase — dueño de las 3 colecciones.

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-B3 (cero secretos hardcodeados) | Sí | Credenciales de Gmail reutilizadas de `configuracion_sistema` (mismas que Disrupciones) |
| REG-F1 (integración reemplazable) | Sí | Envío de email detrás de una interfaz propia, reutilizable |
| REG-G1 (autoservicio primero) | Sí | Búsqueda/artículo no requieren sesión; solo escalar la exige |
| REG-J9 (filtros instantáneos) | Sí | Búsqueda de artículos |

Sin violaciones.

---

## Estructura del proyecto

```text
app/centro_ayuda/
├── __init__.py
├── router_articulos.py     # RF-AYU-001,002,003
├── router_escalacion.py    # RF-AYU-004
├── schemas.py
├── services/
│   ├── ayuda_service.py
│   └── escalacion_service.py   # reutiliza el cliente Gmail de Disrupciones (envío, no solo monitoreo)
├── repositories/
│   └── ayuda_repo.py
├── templates/
│   └── buscar_ayuda.html, articulo_ayuda.html
└── tests/
    ├── test_articulos.py
    └── test_escalacion.py
```

**Decisión de estructura:** `escalacion_service.py` reutiliza `app/disrupciones/integrations/gmail_client.py` (o su equivalente ya implementado) para el **envío** — Disrupciones ya lo usa para **monitorear** (leer) la bandeja; ambos casos de uso comparten la misma cuenta/credenciales OAuth, solo cambia la operación (leer vs. enviar). No crear una integración Gmail paralela.

---

## Modelo de datos (resumen)

| Entidad | Rol | Validaciones clave |
|---|---|---|
| `articulos_ayuda` | Base de conocimiento | `activo` controla visibilidad en búsqueda |
| `articulo_calificaciones` | Pulgar arriba/abajo | `pasajero_id` nullable — calificación anónima permitida |
| `casos_escalados` | Casos derivados a soporte humano | `gmail_thread_id` vincula al hilo real; `estado` gestionado por CU-T36 |

---

## Fases de implementación

### Fase 1 — Buscar y ver artículos (RF-AYU-001, 002)
**Precondición externa:** `specs/tactico/centro-ayuda/` (CU-T28) para tener artículos reales — mientras tanto, sembrar algunos manualmente para pruebas.
**Entregable:** `router_articulos.py`.

### Fase 2 — Calificar artículo (RF-AYU-003)
**Precondición externa:** Fase 1 completa.
**Entregable:** extiende `router_articulos.py`.

### Fase 3 — Escalar caso (RF-AYU-004)
**Precondición externa:** integración Gmail ya configurada (reutilizada de Disrupciones); Seguridad Fase 1 (sesión).
**Entregable:** `router_escalacion.py`, `escalacion_service.py`.

---

## Complexity Tracking

*No aplica.*
