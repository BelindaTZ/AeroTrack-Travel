# Plan de Implementación — Autos

**Módulo:** Autos
**Prefijo:** AUT
**Spec:** [`autos-spec.md`](./autos-spec.md)
**Código fuente:** `app/autos/` *(Fase 1+2 implementadas y verificadas 2026-07-19; Fase 3 resuelta vía Carrito)*
**Fecha:** 2026-07-18
**Estado:** Fase 1 (catálogo) y Fase 2 (búsqueda/detalle/filtros) implementadas y probadas (12 tests: 5 catálogo + 7 búsqueda). Fase 3 (selección) no tiene código propio — se resolvió reutilizando `app/carrito/` (ver `tasks.md`, decisión de alcance).

---

## Resumen

Sostener el catálogo operativo de autos de renta: generación automática vía Global Rental Cars (priorizando Expedia por no tener el problema de fecha/ubicación de Priceline/Booking), búsqueda/filtro/detalle para el pasajero, y selección con revalidación obligatoria contra la fuente antes de confirmar. El módulo más simple de las 4 verticales nuevas de producto (una sola tabla propia, sin tarifas ni reseñas separadas). Cubre 5 RF, 2 RNF y 3 RN sobre 5 CU (CU-O61–O64, O119).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2, design system v4; cliente HTTP para Global Rental Cars (3 sub-proveedores: Priceline, Booking, Expedia — ver `docs/apis-reference.md`).
**Almacenamiento:** PocketBase (`pocketbase-travel`) — este módulo es dueño de `autos_catalogo`, la única colección propia.
**Pruebas:** pytest + `httpx.AsyncClient`, mismo patrón que los módulos ya construidos.
**Restricciones:** cero secretos hardcodeados (REG-B3); auditoría de mutaciones (REG-B4); RN-AUT-001 es una restricción de correctitud, no solo de estilo — ninguna oferta de Priceline/Booking se cobra sin revalidar.
**Escala/alcance:** el módulo más pequeño de las verticales nuevas — 5 RF, 2 RNF, 3 RN, 4 endpoints, 1 colección propia.

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-B3 (cero secretos hardcodeados) | Sí | Credenciales de Global Rental Cars en `configuracion_sistema`/env |
| REG-B4 (auditoría inmutable) | Sí | Selección de auto dispara `audit_service` |
| REG-F1 (integración reemplazable) | Sí | Cliente Global Rental Cars aislado detrás de `rentalcars_client.py` |
| REG-G2 (transparencia de precio) | Sí | RF-AUT-005 revalida antes de cobrar, nunca cobra un precio distinto al mostrado |
| REG-J9 (filtros instantáneos) | Sí | RF-AUT-003 sin botón "Aplicar" |

Sin violaciones — no se llena Complexity Tracking.

---

## Estructura del proyecto

```text
specs/operativo/autos/
├── autos-spec.md
├── plan.md
├── tasks.md
└── checklist.md
```

Código propuesto (mismo patrón que Hoteles):

```text
app/autos/
├── __init__.py
├── router_busqueda.py       # RF-AUT-001,002,003
├── router_seleccion.py      # RF-AUT-005
├── schemas.py
├── services/
│   ├── catalogo_service.py    # RF-AUT-004 (CU-O119)
│   ├── rentalcars_client.py   # cliente de los 3 sub-proveedores
│   └── seleccion_service.py   # RF-AUT-005, revalidación (RN-AUT-001)
├── repositories/
│   └── autos_repo.py
├── templates/
│   └── buscar_autos.html, detalle_auto.html
└── tests/
    ├── test_busqueda.py
    ├── test_catalogo_service.py
    └── test_seleccion.py
```

---

## Modelo de datos (resumen — detalle completo en `docs/aerotrack-travel-propuesta-tablas-v3.dbml`)

| Entidad | Rol en este módulo | Validaciones clave (spec) |
|---|---|---|
| `autos_catalogo` | Única colección propia — catálogo de vehículos | `proveedor_agregador` determina si aplica revalidación obligatoria (RN-AUT-001); `fuente_oferta_ref` es el token para revalidar |

---

## Contratos de API

Ver la tabla completa "Entradas y salidas" en `autos-spec.md`.

- **Búsqueda/detalle:** `GET /autos/buscar`, `GET /autos/{id}`.
- **Catálogo (interno):** `POST /internal/autos/generar-catalogo`.
- **Selección:** `POST /autos/{id}/seleccionar`.

---

## Fases de implementación

### Fase 1 — Generación de catálogo (RF-AUT-004)
**Estado:** ✅ Hecho 2026-07-19.
**Entregable:** `rentalcars_client.py` (solo Expedia), `catalogo_service.py`, `router_interno.py`, `dags/dag_generar_catalogo_autos.py`. Credenciales en `configuracion_sistema` (categoría `autos`, `scripts/seed_autos_config.py`).

### Fase 2 — Búsqueda, detalle y filtros (RF-AUT-001, 002, 003)
**Estado:** ✅ Hecho 2026-07-19.
**Entregable:** `router_busqueda.py` con filtros instantáneos (categoría, transmisión, precio — marca/proveedor sin dato real discriminante), `templates/buscar_autos.html`, `templates/detalle_auto.html`.

### Fase 3 — Selección (RF-AUT-005)
**Estado:** ✅ Hecho 2026-07-19, sin código propio — resuelto reutilizando el motor genérico de `app/carrito/` (`router_vista.py`, nuevo: `POST /carrito/agregar`, `GET /carrito/ver`, `POST /carrito/eliminar/{id}`, `POST /carrito/confirmar`). El detalle de auto postea directo ahí. La revalidación en vivo contra `fuente_oferta_ref` (RN-AUT-001, relevante solo si se implementan Priceline/Booking) queda como brecha abierta documentada — Carrito revalida contra el catálogo interno vigente (RN-CAR-001), no contra una llamada en vivo al proveedor.

---

## Complexity Tracking

*No aplica.*
