# Plan de Implementación — Pasajeros (Táctico)

**Módulo:** Pasajeros
**Prefijo:** PAS
**Spec:** [`pasajeros-spec.md`](./pasajeros-spec.md)
**Código fuente:** `app/pasajeros/` *(nivel Operativo ya implementado — 14/14 tests reales pasando)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. Bloqueado por `reserva_items` (Reservas) para el cálculo real de frecuencia/destino.

---

## Resumen

Segmentación de pasajeros por frecuencia de viaje y destino preferido, y exportación filtrada respetando minimización de datos. Cubre 2 RF y 2 RN sobre 2 CU (CU-T04, T05). Sin colección propia — agrega sobre `pasajeros`/`reservas`/`reserva_items`.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** ninguna nueva. **Almacenamiento:** sin colecciones nuevas — agregación sobre datos existentes. **Restricciones:** REG-B2 (minimización de datos personales) en la exportación.

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Ambos endpoints protegidos |
| REG-B2 (minimización de datos personales) | Sí | RN-PAS-T02 — exportación con campos acotados |
| REG-J9 (filtros instantáneos) | Sí | Segmentación de CU-T04 |

Sin violaciones.

---

## Estructura del proyecto

```text
app/pasajeros/
├── router_segmentacion.py   # RF-PAS-T01, T02 (nuevo)
└── tests/
    └── test_segmentacion.py
```

---

## Fases de implementación

### Fase 1 — Ver segmentación (RF-PAS-T01)
**Precondición externa:** `reserva_items` (Reservas, migración pendiente) para frecuencia/destino real — con datos de prueba sembrados manualmente se puede validar el mecanismo mientras tanto.
**Entregable:** `router_segmentacion.py`.

### Fase 2 — Exportar base (RF-PAS-T02)
**Precondición externa:** Fase 1 completa.
**Entregable:** extiende `router_segmentacion.py` con el endpoint de exportación.

---

## Complexity Tracking

*No aplica.*
