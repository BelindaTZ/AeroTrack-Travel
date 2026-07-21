# Plan de Implementación — Vuelos (Táctico)

**Módulo:** Vuelos (catálogo)
**Prefijo:** VUE
**Spec:** [`vuelos-spec.md`](./vuelos-spec.md)
**Código fuente:** `app/vuelos/` *(nivel Operativo ya implementado — 20/20 tests reales pasando)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. CU-T39/T40/T41 son precondición real de CU-O114–O117 (Operativo, pendientes) — priorizar sobre CU-T06/T07/T08 si el objetivo es desbloquear asientos/cabina.

---

## Resumen

Configuración/monitoreo del catálogo ya en producción (CU-T06/T07/T08) y las 3 configuraciones que la nueva funcionalidad de asientos/cabina necesita antes de poder implementarse (CU-T39/T40/T41). Cubre 6 RF y 3 RN. Sin colección propia — todo vive en `configuracion_sistema`.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** ninguna nueva. **Almacenamiento:** sin colecciones nuevas — todo en `configuracion_sistema` (categoría `disponibilidad_asientos` ya definida en el dbml v3 para T39/T40).

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Los 6 endpoints protegidos |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T08 |

Sin violaciones.

---

## Estructura del proyecto

```text
app/vuelos/
├── router_config_catalogo.py       # RF-VUE-T01, T02 (nuevo)
├── router_reporte_rutas.py         # RF-VUE-T03 (nuevo)
├── router_config_asientos.py       # RF-VUE-T04, T05, T06 (nuevo)
└── tests/
    ├── test_config_catalogo.py
    ├── test_reporte_rutas.py
    └── test_config_asientos.py
```

---

## Fases de implementación

### Fase 1 — Configurar y monitorear catálogo (RF-VUE-T01, T02)
**Precondición externa:** ninguna — el catálogo (CU-O19) ya está en producción.
**Entregable:** `router_config_catalogo.py`.

### Fase 2 — Reporte de rutas (RF-VUE-T03)
**Precondición externa:** retrofit de `busquedas_recientes` (ver `cuenta-mis-viajes-spec.md`) y `reserva_items` (Reservas) para conversión real.
**Entregable:** `router_reporte_rutas.py`.

### Fase 3 — Configuración de asientos/cabina (RF-VUE-T04, T05, T06)
**Precondición externa:** ninguna para implementar esta fase en sí — pero es **precondición de** Vuelos Operativo Fase 9 (CU-O114–O117). **Priorizar esta fase si el objetivo es desbloquear esa funcionalidad Operativa.**
**Entregable:** `router_config_asientos.py`.

---

## Complexity Tracking

*No aplica.*
