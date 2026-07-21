# Plan de Implementación — Reservas (Táctico)

**Módulo:** Reservas
**Prefijo:** RES
**Spec:** [`reservas-spec.md`](./reservas-spec.md)
**Código fuente:** `app/reservas/` *(nivel Operativo ya implementado — 21/21 tests reales pasando)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. CU-T18 es de las piezas tácticas más transversales de todo el catálogo — consumida por 5 verticales de producto, no solo por Reservas.

---

## Resumen

Reporte de reservas por estado (CU-T16), monitoreo proactivo de reservas por vencer (CU-T17) y configuración centralizada de políticas de reembolso por producto/tarifa (CU-T18, consumida transversalmente). Cubre 3 RF y 2 RN. Sin colección propia nueva — `politicas_reembolso` ya existe en el dbml v3 desde antes de esta ronda.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** ninguna nueva. **Almacenamiento:** dueño editorial de `politicas_reembolso` (la tabla ya existe, este nivel es la primera UI real de edición).

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Distinguir Agente (CU-T17) de Administrador (CU-T16, T18) — mismo punto de atención que Centro de Ayuda CU-T36 |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T16 |

Sin violaciones.

---

## Estructura del proyecto

```text
app/reservas/
├── router_reporte_estado.py     # RF-RES-T01 (nuevo)
├── router_proximas_vencer.py    # RF-RES-T02 (nuevo)
├── router_politicas.py          # RF-RES-T03 (nuevo)
└── tests/
    ├── test_reporte_estado.py
    ├── test_proximas_vencer.py
    └── test_politicas.py
```

---

## Fases de implementación

### Fase 1 — Reporte por estado (RF-RES-T01)
**Precondición externa:** ninguna — reservas ya existen en producción.
**Entregable:** `router_reporte_estado.py`.

### Fase 2 — Monitorear próximas a vencer (RF-RES-T02)
**Precondición externa:** ninguna — CU-O44 ya implementado y probado.
**Entregable:** `router_proximas_vencer.py`. **Verificar RBAC de rol Agente**, no solo Administrador.

### Fase 3 — Configurar políticas de reembolso (RF-RES-T03)
**Precondición externa:** ninguna para implementar en sí — pero **desbloquea configuración real para las 5 verticales de producto** que hoy usan valores sembrados manualmente o defaults.
**Entregable:** `router_politicas.py`.

---

## Complexity Tracking

*No aplica.*
