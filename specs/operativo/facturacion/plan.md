# Plan de Implementación — Facturación

**Módulo:** Facturación
**Prefijo:** FAC
**Spec:** [`facturacion-spec.md`](./facturacion-spec.md)
**Código fuente:** `app/facturacion/`
**Fecha:** 2026-07-09
**Estado:** Draft — pendiente de revisión antes de iniciar implementación

---

## Resumen

Procesar todo movimiento de dinero del sistema: pago de reserva, factura, comisión, conciliación, remesa simulada, reembolso, y el mecanismo de cobro/reembolso de diferencia de tarifa disparado desde Reservas — todo vía Stripe test mode, con idempotencia y trazabilidad completas. Cubre 10 RF y 2 RNF sobre 9 CU (CU-O32–O40, O47).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2 + Bootstrap 5; SDK oficial de Stripe (test mode, REG-I5); cliente PocketBase para `pagos`, `comisiones`, `remesas`, `remesa_comisiones`, `reembolsos`, `facturas`, `metodos_pago`; librería de generación de PDF (p. ej. WeasyPrint o ReportLab) para facturas e itinerarios.
**Almacenamiento:** PocketBase (colecciones propias) + Stripe (fuente de verdad del estado real de cobro/reembolso, referenciado vía `stripe_payment_intent_id`/`stripe_refund_id`).
**Pruebas:** pytest + `httpx.AsyncClient`; Stripe test mode con tarjetas de prueba documentadas por Stripe; prueba de idempotencia dedicada (RNF-FAC-002); prueba de la condición de carrera pago/expiración (RN-FAC-006, complementa RN-RES-005).
**Plataforma objetivo:** contenedor Linux vía Docker/docker-compose.
**Tipo de proyecto:** servicio web con integración de pagos.
**Objetivos de rendimiento:** ninguno específico más allá de los límites de latencia de Stripe test mode; el desglose de precio se muestra antes de cualquier cobro (REG-G2).
**Restricciones:** nunca se almacena un número de tarjeta completo (REG-C1); todo cobro/reembolso es idempotente por `stripe_payment_intent_id`/`stripe_refund_id` (REG-D1); las políticas de reembolso se resuelven por reglas, nunca por excepción manual (REG-D3).
**Escala/alcance:** 10 RF, dueño de 7 colecciones, única integración de pago del sistema.

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-C1 (no tarjetas crudas) | Sí | Todo dato de tarjeta se captura vía Stripe Elements/Checkout del lado cliente; el backend solo recibe tokens |
| REG-D1 (idempotencia) | Sí | `stripe_payment_intent_id` único por intento; prueba explícita de doble envío del mismo evento |
| REG-D2 (trazabilidad) | Sí | Todo movimiento tiene origen/destino/estado consultable end-to-end desde una reserva |
| REG-D3 (reembolso por reglas) | Sí | `reembolso_service.py` no expone ningún parámetro de "override manual" de monto/porcentaje |
| REG-F1/F2/F3 (Stripe reemplazable, timeouts, aislamiento) | Sí | Cliente de Stripe detrás de una interfaz `payment_gateway.py` |
| REG-J4 (tipografía tabular para cifras) | Sí | Templates de historial de pagos/comisiones usan la fuente monoespaciada definida en `reglas.md` REG-J4 |

Sin violaciones — no se llena Complexity Tracking.

---

## Estructura del proyecto

### Documentación (este módulo)

```text
specs/operativo/facturacion/
├── facturacion-spec.md
├── plan.md
└── checklist.md
```

### Código fuente

```text
app/facturacion/
├── __init__.py
├── router_pagos.py            # RF-FAC-001, 008
├── router_documentos.py       # RF-FAC-009, 010
├── router_backoffice.py       # RF-FAC-004, 005
├── router_diferencia.py       # RF-FAC-007 (CU-O47, consumido internamente por Reservas)
├── schemas.py
├── services/
│   ├── pago_service.py         # RF-FAC-001, incluye RNF-FAC-002 (idempotencia)
│   ├── factura_service.py      # RF-FAC-002
│   ├── comision_service.py     # RF-FAC-003, 004
│   ├── remesa_service.py       # RF-FAC-005
│   ├── reembolso_service.py    # RF-FAC-006, aplica RN-FAC-001
│   ├── diferencia_tarifa_service.py  # RF-FAC-007
│   └── documentos_service.py   # RF-FAC-009, 010 (generación de PDF)
├── integrations/
│   └── payment_gateway.py      # abstracción sobre el SDK de Stripe
├── repositories/
│   └── pocketbase_client.py
├── templates/
│   ├── checkout_pago.html, historial_pagos.html
│   └── backoffice/ (comisiones.html, remesas.html)
└── tests/
    ├── test_pago.py             # incluye prueba de idempotencia
    ├── test_factura_comision.py
    ├── test_conciliacion_remesa.py
    ├── test_reembolso.py
    ├── test_diferencia_tarifa.py
    └── test_documentos.py
```

**Decisión de estructura:** `payment_gateway.py` es el único punto de contacto con el SDK de Stripe en todo el sistema — ningún otro módulo (incluido Reservas) importa el SDK directamente; siempre pasa por `router_diferencia.py`/los servicios de este módulo.

---

## Modelo de datos (resumen)

| Entidad | Rol en este módulo |
|---|---|
| `pagos`, `metodos_pago` | Dueño |
| `comisiones` | Dueño |
| `remesas`, `remesa_comisiones` | Dueño |
| `reembolsos` | Dueño |
| `facturas` | Dueño |
| `reservas` | Lectura (Reservas) — origen de todo movimiento |
| `politicas_reembolso`, `aerolineas` | Lectura (Vuelos) |

---

## Contratos de API

- `POST /reservas/{id}/pagar`, `GET /pagos` — RF-FAC-001, 008.
- `GET /facturas/{id}/pdf`, `GET /reservas/{id}/itinerario-pdf` — RF-FAC-009, 010.
- `GET/POST /backoffice/comisiones`, `POST /backoffice/comisiones/{id}/marcar-cobrada`, `POST /backoffice/remesas` — RF-FAC-004, 005.
- `POST /internal/reembolsos` — RF-FAC-006.
- `POST /internal/reservas/{id}/diferencia-tarifa` — RF-FAC-007.

---

## Fases de implementación

### Fase 1 — Procesar pago de reserva (RF-FAC-001)
**Precondición externa:** Reservas Fase 1 (crear reserva) completa — necesita reservas `pendiente_pago` reales.
**Entregable:** `pago_service.py`, `payment_gateway.py`, prueba de idempotencia (RNF-FAC-002).
**Nota de secuencia:** se implementa primero porque Reservas Fase 3 (expiración) necesita este servicio disponible para completar su prueba de condición de carrera (RN-RES-005/RN-FAC-006).

### Fase 2 — Factura y comisión (RF-FAC-002, 003)
**Precondición externa:** Fase 1 completa.
**Entregable:** `factura_service.py`, `comision_service.py`, `documentos_service.py` (generación de PDF).

### Fase 3 — Consulta y descarga de documentos (RF-FAC-008, 009, 010)
**Precondición externa:** Fase 2 completa.
**Entregable:** `router_pagos.py`, `router_documentos.py`.

### Fase 4 — Reembolso (RF-FAC-006)
**Precondición externa:** Fase 1 completa; Vuelos dueño de `politicas_reembolso` disponible.
**Entregable:** `reembolso_service.py` — desbloquea a Reservas Fase 5 (CU-O24) y a Disrupciones Fase 3 (CU-O30 → CU-O37).

### Fase 5 — Diferencia de tarifa (RF-FAC-007, CU-O47)
**Precondición externa:** Fase 1 y Fase 4 completas (reutiliza ambos mecanismos con signo).
**Entregable:** `diferencia_tarifa_service.py`, `router_diferencia.py` — desbloquea a Reservas Fase 5 (CU-O23).

### Fase 6 — Conciliación y remesas (RF-FAC-004, 005)
**Precondición externa:** Fase 2 completa (necesita comisiones reales); Seguridad Fase 2 (RBAC) completa.
**Entregable:** `router_backoffice.py`, `remesa_service.py`.

---

## Complexity Tracking

*No aplica.*
