# Plan de Implementación — Actividades

**Módulo:** Actividades
**Prefijo:** ACT
**Spec:** [`actividades-spec.md`](./actividades-spec.md)
**Código fuente:** `app/actividades/` *(Fase 1-3 implementadas y verificadas 2026-07-19; Fase 4 resuelta vía Carrito)*
**Fecha:** 2026-07-18
**Estado:** Fase 1+2 (catálogo+reseñas+disponibilidad sintética) y Fase 3 (búsqueda/detalle/filtros/horarios/reseñas) implementadas y probadas (5+7=12 tests). Fase 4 (selección) resuelta reutilizando `app/carrito/` — brecha real: no valida cupo insuficiente antes de confirmar (ver `checklist.md` CHK012).

---

## Resumen

Sostener el catálogo operativo de actividades: generación vía Travel Advisor (catálogo + reseñas embebidas), disponibilidad **sintética** por regla de negocio (gap real confirmado, sin fuente de inventario real), búsqueda/filtro/detalle, y selección con cálculo de precio por participantes. Cubre 9 RF, 1 RNF y 3 RN sobre 8 CU (CU-O65–O70, O120, O121).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2, design system v4; cliente HTTP para Travel Advisor (2 endpoints reales: `v2/list` + `get-details` legacy).
**Almacenamiento:** PocketBase — dueño de `actividades_catalogo`, `actividades_horarios`, `actividades_resenas`.
**Pruebas:** pytest + `httpx.AsyncClient`.
**Restricciones:** RF-ACT-006 debe dejar explícito en el dato/documentación que el cupo es sintético (RN-ACT-002), nunca presentarlo como inventario real.
**Escala/alcance:** 9 RF, 1 RNF, 3 RN, 7 endpoints, 3 colecciones propias.

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-B3 (cero secretos hardcodeados) | Sí | Credenciales de Travel Advisor en `configuracion_sistema`/env |
| REG-B4 (auditoría inmutable) | Sí | Selección de actividad audita |
| REG-F1 (integración reemplazable) | Sí | `traveladvisor_client.py` aislado |
| REG-J9 (filtros instantáneos) | Sí | RF-ACT-003 sin botón "Aplicar" |
| REG-H1 (equivalente para datos sintéticos) *(no es principio de IA, pero mismo espíritu)* | Sí | RN-ACT-002 — nunca presentar dato sintético como real |

Sin violaciones — no se llena Complexity Tracking.

---

## Estructura del proyecto

```text
app/actividades/
├── __init__.py
├── router_busqueda.py       # RF-ACT-001,002,003,009
├── router_horarios.py       # RF-ACT-007,008
├── schemas.py
├── services/
│   ├── catalogo_service.py       # RF-ACT-004,005 (CU-O120)
│   ├── traveladvisor_client.py   # cliente de 2 endpoints reales
│   ├── disponibilidad_service.py # RF-ACT-006 (CU-O121)
│   └── seleccion_service.py      # RF-ACT-008
├── repositories/
│   └── actividades_repo.py
├── templates/
│   └── buscar_actividades.html, detalle_actividad.html
└── tests/
    ├── test_busqueda.py
    ├── test_catalogo_service.py
    ├── test_disponibilidad_service.py
    └── test_seleccion.py
```

---

## Modelo de datos (resumen)

| Entidad | Rol | Validaciones clave |
|---|---|---|
| `actividades_catalogo` | Catálogo real de Travel Advisor | `inclusiones`/`punto_encuentro`/`condiciones` solo por curación manual (RN-ACT-001) |
| `actividades_horarios` | Disponibilidad **sintética** | Generada por regla de negocio (CU-T42), no por API |
| `actividades_resenas` | Reseñas reales, embebidas en `get-details` | Sin llamada de API separada |

---

## Fases de implementación

### Fase 1 — Generación de catálogo y reseñas (RF-ACT-004, 005) + Fase 2 — Disponibilidad sintética (RF-ACT-006)
**Estado:** ✅ Hecho 2026-07-19 — implementadas juntas en `catalogo_service.py` (sin esto una actividad recién catalogada no sería reservable de inmediato). Parámetros de `configuracion_sistema.disponibilidad_actividades.*` sembrados directo (`scripts/seed_actividades_config.py`), CU-T42/Táctico sigue sin UI de edición.
**Entregable:** `traveladvisor_client.py`, `catalogo_service.py`, `router_interno.py`, `dags/dag_generar_catalogo_actividades.py`.

### Fase 3 — Búsqueda, detalle, filtros, horarios y reseñas (RF-ACT-001, 002, 003, 007, 009)
**Estado:** ✅ Hecho 2026-07-19.
**Entregable:** `router_busqueda.py` (busca+detalle en un router, sin `router_horarios.py` separado), `templates/buscar_actividades.html`, `templates/detalle_actividad.html`.

### Fase 4 — Seleccionar (RF-ACT-008)
**Estado:** ✅ Hecho 2026-07-19, sin código propio — el detalle postea directo a `app/carrito/router_vista.py` (`POST /carrito/agregar`), precio total (unitario × participantes) calculado en JS. **Brecha real, no resuelta:** ninguna capa valida que `participantes <= cupos_disponibles` antes de confirmar — ver `checklist.md` CHK012.

---

## Complexity Tracking

*No aplica.*
