# Plan de Implementación — Cruceros

**Módulo:** Cruceros
**Prefijo:** CRU
**Spec:** [`cruceros-spec.md`](./cruceros-spec.md)
**Código fuente:** `app/cruceros/` *(Fase 1-3 implementadas y verificadas 2026-07-19; Fase 4 resuelta vía Carrito)*
**Fecha:** 2026-07-18
**Estado:** Fase 1+2 (catálogo real + disponibilidad sintética) y Fase 3 (búsqueda/itinerario/barco/comparación) implementadas y probadas (3+6=9 tests). Fase 4 (selección) resuelta reutilizando `app/carrito/` — brecha real: no valida cupo insuficiente antes de confirmar (ver `checklist.md` CHK008).

---

## Resumen

Sostener el catálogo operativo de cruceros: generación vía Cruise Pricing API (navieras, barcos, itinerarios, precio por camarote), disponibilidad **sintética** de camarotes (gap real confirmado, sin inventario expuesto por la API), búsqueda/itinerario/información de barco/comparación de fechas, y selección de camarote. Cubre 7 RF, 1 RNF y 2 RN sobre 7 CU (CU-O71–O75, O122, O123).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2, design system v4; cliente HTTP para Cruise Pricing API. **Almacenamiento:** PocketBase — dueño de `navieras`, `barcos`, `cruceros_catalogo`, `cruceros_camarotes_tarifa`. **Pruebas:** pytest + `httpx.AsyncClient`. **Restricciones:** RF-CRU-006 debe dejar explícito que el cupo es sintético (RN-CRU-001).

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-B3 (cero secretos hardcodeados) | Sí | Credenciales de Cruise Pricing API en `configuracion_sistema`/env |
| REG-B4 (auditoría inmutable) | Sí | Selección de camarote audita |
| REG-F1 (integración reemplazable) | Sí | `cruisepricing_client.py` aislado |
| REG-J9 (filtros instantáneos) | Sí | Filtros de búsqueda sin botón "Aplicar" |

Sin violaciones.

---

## Estructura del proyecto

```text
app/cruceros/
├── __init__.py
├── router_busqueda.py       # RF-CRU-001,002,003,004
├── router_seleccion.py      # RF-CRU-007
├── schemas.py
├── services/
│   ├── catalogo_service.py       # RF-CRU-005 (CU-O122)
│   ├── cruisepricing_client.py   # cliente de Cruise Pricing API
│   ├── disponibilidad_service.py # RF-CRU-006 (CU-O123)
│   └── seleccion_service.py      # RF-CRU-007
├── repositories/
│   └── cruceros_repo.py
├── templates/
│   └── buscar_cruceros.html, itinerario_crucero.html
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
| `navieras` | Catálogo de navieras, cache de destinos | — |
| `barcos` | Info de barco por naviera | — |
| `cruceros_catalogo` | Catálogo real de zarpes | `itinerario_puertos` es el orden real día a día |
| `cruceros_camarotes_tarifa` | Precio real por tipo de camarote; `cupos_disponibles` **sintético** | RN-CRU-001 |

---

## Fases de implementación

### Fase 1 — Generación de catálogo (RF-CRU-005) + Fase 2 — Disponibilidad sintética (RF-CRU-006)
**Estado:** ✅ Hecho 2026-07-19 — implementadas juntas en `catalogo_service.py`, mismo criterio que Actividades. `configuracion_sistema.disponibilidad_cruceros.*` sembrado directo (`scripts/seed_cruceros_config.py`), CU-T43/Táctico sigue sin UI de edición.
**Entregable:** `cruisepricing_client.py`, `catalogo_service.py`, `router_interno.py`, `dags/dag_generar_catalogo_cruceros.py`.

### Fase 3 — Búsqueda, itinerario, barco y comparación (RF-CRU-001, 002, 003, 004)
**Estado:** ✅ Hecho 2026-07-19. Bug real corregido en esta fase: `itinerario_puertos` es `[{"day","port"}]`, no strings planos (ver `tasks.md`/`errores-conocidos.md`).
**Entregable:** `router_busqueda.py` (buscar+detalle+comparar fechas, sin sub-rutas separadas), `templates/buscar_cruceros.html`, `detalle_crucero.html`, `comparar_fechas.html`.

### Fase 4 — Selección de camarote (RF-CRU-007)
**Estado:** ✅ Hecho 2026-07-19, sin código propio — el detalle postea directo a `app/carrito/router_vista.py`. **Brecha real, no resuelta:** ninguna capa valida cupo server-side antes de confirmar (solo gate de presentación) — ver `checklist.md` CHK008.

---

## Complexity Tracking

*No aplica.*
