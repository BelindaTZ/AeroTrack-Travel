# Plan de Implementación — Asistente IA (Táctico)

**Módulo:** Asistente IA
**Prefijo:** IA
**Spec:** [`asistente-ia-spec.md`](./asistente-ia-spec.md)
**Código fuente:** `app/asistente_ia/` *(compartido con el nivel Operativo)*
**Fecha:** 2026-07-18
**Estado:** ✅ Implementado 2026-07-19 — ver [`checklist.md`](./checklist.md).

---

## Resumen

Configuración de tono/temas/respuestas predefinidas (CU-T34, consumida directamente por el nivel Operativo, refuerzo adicional de REG-H1) y reporte de consultas frecuentes/sin respuesta (CU-T33, insumo directo para la base de conocimiento de Centro de Ayuda). Cubre 2 RF y 2 RN. Sin colección propia nueva.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2. **Almacenamiento:** config en `configuracion_sistema`; lectura de `mensajes_ia` (Operativo).

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-H1 (contexto acotado y verificable) | Sí | CU-T34 (temas permitidos) es una capa de control adicional sobre este principio, no solo estilo |
| REG-B1 (RBAC) | Sí | Ambos endpoints protegidos |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T33 |

Sin violaciones.

---

## Fases de implementación

### Fase 1 — Configurar el asistente (RF-IA-T01, CU-T34)
**Precondición externa:** ninguna — implementar en paralelo con Operativo Fase 2/3, no después (los temas permitidos condicionan RN-IA-001 desde el inicio).
**Entregable:** `router_config_asistente.py`.

### Fase 2 — Reporte de consultas frecuentes (RF-IA-T02, CU-T33)
**Precondición externa:** `mensajes_ia` con datos reales (Operativo Fase 2/3).
**Entregable:** `router_reporte_asistente.py`.

---

## Complexity Tracking

*No aplica.*
