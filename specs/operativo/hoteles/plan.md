# Plan de Implementación — Hoteles

**Módulo:** Hoteles
**Prefijo:** HOT
**Spec:** [`hoteles-spec.md`](./hoteles-spec.md)
**Código fuente:** `app/hoteles/` *(Fase 1-4 completas 2026-07-19 — solo pago diferido sin implementar)*
**Fecha:** 2026-07-18 (Fase 1: 2026-07-19, Fase 2: 2026-07-19, Fase 3+4/cupo: 2026-07-19 segunda ronda)
**Estado:** Fase 1 (catálogo), Fase 2 (búsqueda/detalle/filtros/reseñas/comparación reembolsable) y Fase 3 (cargos locales, 99 ciudades reales) implementadas y probadas (4+7+6=17 tests). Fase 4: selección funciona vía Carrito con cupo real validado server-side; solo pago diferido (RF-HOT-009) sigue sin código — ver `checklist.md`.

---

## Resumen

Sostener el catálogo operativo de hoteles: generación automática vía HotelLens (3 pasos: descubrimiento → comparador de OTAs → detalle real de Booking.com con cupo/cancelación reales), búsqueda/filtro/detalle para el pasajero, comparación de habitaciones reembolsables vs. no reembolsables, reseñas cacheadas, cargos locales (fuente CSV manual), y reserva con pago diferido. Cubre 9 RF, 2 RNF y 4 RN sobre 8 CU (CU-O54–O60, O118).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2 + Bootstrap 5/design system v4 (REG-I2); SDK/cliente HTTP de PocketBase para `hoteles_catalogo`, `hoteles_tarifas`, `hoteles_resenas`, `cargos_locales_destino`; cliente HTTP para HotelLens (3 endpoints reales, ver `docs/apis-reference.md`).
**Almacenamiento:** PocketBase (`pocketbase-travel`) — este módulo es dueño de las 4 colecciones listadas.
**Pruebas:** pytest + `httpx.AsyncClient`, contra una instancia PocketBase de test — mismo patrón que los 6 módulos ya construidos.
**Plataforma objetivo:** contenedor Linux vía Docker/docker-compose (REG-I4), mismo `app-travel`.
**Restricciones:** cero secretos hardcodeados (REG-B3, credenciales de HotelLens en `configuracion_sistema`/env); auditoría de mutaciones (REG-B4); el cupo/cancelación mostrados son datos reales del proveedor, nunca aproximados (RN-HOT-001/002).
**Escala/alcance:** módulo de catálogo — 9 RF, 2 RNF, 4 RN, ~6 endpoints, 4 colecciones PocketBase propias.

---

## Constitution Check

*GATE: debe pasar antes de iniciar implementación de cada fase.*

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-A1 (separación transaccional/analítica) | No aplica directamente | Este módulo no toca el modelo dimensional heredado (ese es exclusivo de Vuelos) |
| REG-B3 (cero secretos hardcodeados) | Sí | Credenciales de HotelLens en `configuracion_sistema`/env, nunca en código |
| REG-B4 (auditoría inmutable) | Sí | Toda reserva/mutación de este módulo dispara `audit_service` (ya existe en Seguridad, se reutiliza) |
| REG-F1 (integración externa reemplazable) | Sí | Cliente HotelLens aislado detrás de una interfaz propia (`hotellens_client.py`), sin acoplar el resto del módulo al proveedor específico |
| REG-G2 (transparencia de precio) | Sí | RF-HOT-006 muestra reembolsable/cancelación como dato real antes de confirmar, nunca oculto |
| REG-J9 (filtros instantáneos) | Sí | RF-HOT-003 sin botón "Aplicar" |
| REG-I9 (ISO/IEC 25010) | Sí | Mismo estándar de calidad transversal que el resto del sistema |

Sin violaciones que requieran justificación — no se llena Complexity Tracking.

---

## Estructura del proyecto

### Documentación (este módulo)

```text
specs/operativo/hoteles/
├── hoteles-spec.md   # Especificación (ya generada)
├── plan.md           # Este archivo
├── tasks.md          # Desglose de tareas
└── checklist.md      # Checklist de validación contra RF/RN
```

### Código fuente (propuesto, mismo patrón que Vuelos)

```text
app/hoteles/
├── __init__.py
├── router_busqueda.py       # RF-HOT-001,002,003 — buscar, detalle, filtros
├── router_resenas.py        # RF-HOT-007
├── router_cargos.py         # RF-HOT-008
├── router_seleccion.py      # RF-HOT-006,009 — seleccionar habitación, pago diferido
├── schemas.py
├── services/
│   ├── catalogo_service.py    # RF-HOT-004,005 (CU-O118) — job de sincronización
│   ├── hotellens_client.py    # cliente HTTP de los 3 endpoints reales de HotelLens
│   └── seleccion_service.py   # RF-HOT-006,009
├── repositories/
│   └── hoteles_repo.py        # usa app/shared/pocketbase_client.py
├── templates/
│   ├── buscar_hoteles.html, detalle_hotel.html
│   └── (reutiliza patrones de `.card`/`.tag` del design system v4)
└── tests/
    ├── test_busqueda.py
    ├── test_catalogo_service.py
    ├── test_seleccion.py
    └── test_cargos_resenas.py
```

**Decisión de estructura:** mismo patrón por módulo de dominio que Seguridad/Vuelos/Reservas — `hoteles/` no tiene servicios transversales propios (a diferencia de Seguridad), consume `session_service`/`rbac_service`/`audit_service` ya existentes vía `Depends(...)`.

---

## Modelo de datos (resumen — detalle completo de campos en `docs/aerotrack-travel-propuesta-tablas-v3.dbml`)

| Entidad | Rol en este módulo | Validaciones clave (spec) |
|---|---|---|
| `hoteles_catalogo` | Catálogo de hoteles, generado por RF-HOT-004 | `ciudad`/`pais` ya vienen limpios de HotelLens (RNF-HOT-001) |
| `hoteles_tarifas` | Habitaciones/precio por hotel | `cupos_disponibles` es dato real (RN-HOT-001), `reembolsable` es dato real (RN-HOT-002) |
| `hoteles_resenas` | Reseñas cacheadas | `fuente` es texto libre, no enum; `fecha_relativa_texto` no es una fecha parseable |
| `cargos_locales_destino` | Impuestos/tasas locales, importación manual | Sin cobertura completa (~100 ciudades); `regla_texto` es el dato autoritativo (RN-HOT-003) |
| `sincronizaciones_log` (Integraciones, no propia) | Bitácora de cada corrida de RF-HOT-004 | Se escribe, no se lee — dueño real es Integraciones |

---

## Contratos de API

Ver la tabla completa "Entradas y salidas" en `hoteles-spec.md`. Agrupados por fase:

- **Búsqueda/detalle:** `GET /hoteles/buscar`, `GET /hoteles/{id}`, `GET /hoteles/{id}/resenas`, `GET /hoteles/{id}/cargos-locales`.
- **Catálogo (interno):** `POST /internal/hoteles/generar-catalogo`.
- **Selección:** `POST /hoteles/{id}/tarifas/{tarifa_id}/seleccionar`.

---

## Fases de implementación

### Fase 1 — Generación de catálogo (RF-HOT-004, 005)
**Estado:** ✅ Hecho 2026-07-19.
**Entregable:** `hotellens_client.py`, `catalogo_service.py`, `router_interno.py` (`POST /internal/hoteles/generar-catalogo`), `dags/dag_generar_catalogo_hoteles.py`. Credenciales en `configuracion_sistema` (categoría `hoteles`, `scripts/seed_hoteles_config.py`).

### Fase 2 — Búsqueda, detalle, filtros y reseñas (RF-HOT-001, 002, 003, 007)
**Estado:** ✅ Hecho 2026-07-19.
**Entregable:** `router_busqueda.py` (busca+detalle+reseñas+cargos locales en un router), `templates/buscar_hoteles.html`, `detalle_hotel.html`.

### Fase 3 — Cargos locales, datos reales (RF-HOT-008)
**Estado:** ✅ Hecho 2026-07-19 (segunda ronda). `dags/dag_importar_cargos_locales.py` (disparo manual, `schedule=None`) parsea `fuentes_extra/holidu_tourist_tax_por_ciudad.csv` (solo su Tabla 1 — el archivo trae dos tablas concatenadas) y hace upsert en `cargos_locales_destino` vía `POST /internal/hoteles/importar-cargos-locales`. Verificado en vivo: 99 ciudades reales, Paris con su regla compuesta real.

### Fase 4 — Selección de habitación (RF-HOT-006)
**Estado:** ✅ Hecho 2026-07-19, sin código propio — el detalle postea directo a `app/carrito/router_vista.py`. Comparación reembolsable/no reembolsable visible antes de confirmar. Cupo real validado server-side (`app.shared.cupo_service`, generalizado desde Vuelos) antes de crear la reserva.
**Pago diferido (RF-HOT-009):** sigue sin código — `hoteles_tarifas` no tiene campo de modalidad de pago diferido, y depende de CU-O86 (Facturación, tampoco construido).

---

## Complexity Tracking

*No aplica.*
