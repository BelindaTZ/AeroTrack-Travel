# Plan de Implementación — Facturación (Táctico)

**Módulo:** Facturación
**Prefijo:** FAC
**Spec:** [`facturacion-spec.md`](./facturacion-spec.md)
**Código fuente:** `app/facturacion/` *(nivel Operativo ya implementado)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. Ambos CU implementables ya, sobre datos reales existentes.

---

## Resumen

Dashboard financiero en tiempo real (CU-T22) y reporte de ingresos por período/producto (CU-T23), manteniendo siempre separados cargo de servicio (inmediato) y comisión (diferida). Cubre 2 RF y 2 RN. Sin colección propia nueva.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** ninguna nueva. **Almacenamiento:** sin colecciones nuevas — agregación sobre `pagos`/`comisiones`/`remesas`/`facturas` ya existentes.

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Ambos endpoints protegidos |
| REG-D2 (trazabilidad completa de movimiento monetario) | Sí | El dashboard/reporte deben reflejar datos reales, no aproximados |
| REG-J9 (filtros instantáneos) | Sí | Reporte de CU-T23 |

Sin violaciones.

---

## Estructura del proyecto

```text
app/facturacion/
├── router_dashboard_financiero.py   # RF-FAC-T01 (nuevo)
├── router_reporte_ingresos.py       # RF-FAC-T02 (nuevo)
└── tests/
    ├── test_dashboard_financiero.py
    └── test_reporte_ingresos.py
```

---

## Fases de implementación

### Fase 1 — Dashboard financiero (RF-FAC-T01)
**Precondición externa:** ninguna — datos reales ya existen desde Facturación Operativo.
**Entregable:** `router_dashboard_financiero.py`.

### Fase 2 — Reporte de ingresos (RF-FAC-T02)
**Precondición externa:** Fase 1 completa.
**Entregable:** `router_reporte_ingresos.py`, con la separación explícita cargo de servicio/comisión (RN-FAC-T01).

---

## Complexity Tracking

*No aplica.*
