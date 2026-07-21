# Plan de Implementación — Paquetes

**Módulo:** Paquetes
**Prefijo:** PAQ
**Spec:** [`paquetes-spec.md`](./paquetes-spec.md)
**Código fuente:** `app/paquetes/` *(implementado y probado 2026-07-19)*
**Fecha:** 2026-07-18
**Estado:** ✅ Implementado y probado (2026-07-19) — 9/9 tests. `reserva_items` ya existe (Reservas 1.4); este módulo es una capa de orquestación real sobre esa estructura, sin datos propios (salvo `tipos_paquete_descuento`, ya sembrado).

---

## Resumen

Componer un paquete (vuelo+hotel obligatorio, auto/actividad opcional) reutilizando la selección real de cada módulo de producto, con desglose de ahorro transparente y cambio de componente sin perder el resto. Cubre 5 RF y 3 RN sobre 5 CU (CU-O76–O80). Sin colección de catálogo propia — solo consume `tipos_paquete_descuento` (config) y escribe sobre `reserva_items`/`reservas.es_paquete` (Reservas).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2, design system v4; sin cliente HTTP externo (no hay fuente de datos externa para este módulo). **Almacenamiento:** no es dueño de ninguna colección — lee `tipos_paquete_descuento` (nueva, sin dueño claro todavía, candidata a vivir en `app/paquetes/` aunque conceptualmente es config compartida) y escribe sobre `reserva_items`/`reservas` (Reservas). **Restricciones:** RN-PAQ-002 — el descuento se copia al checkout, nunca se recalcula retroactivamente sobre paquetes ya confirmados.

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-G2 (transparencia de precio) | Sí | RF-PAQ-002 desglosa cada componente, nunca un total sin explicar |
| REG-J10 (navegación sin pérdida de estado) | Sí | RF-PAQ-003 — cambiar un componente no reinicia el flujo |
| REG-B4 (auditoría) | Sí | Toda mutación audita |

Sin violaciones.

---

## Estructura del proyecto

```text
app/paquetes/
├── __init__.py
├── router_construccion.py   # RF-PAQ-001,003,005
├── router_resumen.py        # RF-PAQ-002,004
├── schemas.py
├── services/
│   └── paquete_service.py    # orquesta selección de componentes + cálculo de descuento
├── repositories/
│   └── paquetes_repo.py      # lee tipos_paquete_descuento; delega reserva_items a Reservas
├── templates/
│   └── construir_paquete.html, resumen_paquete.html
└── tests/
    ├── test_construccion.py
    └── test_resumen.py
```

**Decisión de estructura:** dueño de la colección `tipos_paquete_descuento` — se decide al implementar si vive en `app/paquetes/` (dominio conceptual) o en `app/shared/` (es config leída por este único módulo, no transversal); se recomienda `app/paquetes/` por tener dueño de dominio claro, mismo criterio que separó `session_service` (transversal, en Seguridad) de config específica de un módulo.

---

## Modelo de datos (resumen)

| Entidad | Rol en este módulo | Validaciones clave |
|---|---|---|
| `tipos_paquete_descuento` | Única colección con posible dueño en este módulo | `combinacion` es texto controlado por UI de admin, no enum cerrado (RF-PAQ-T01 en `specs/tactico/paquetes/`) |
| `reserva_items` (Reservas, no implementada) | Estructura real de un paquete — cada componente es una fila | `reservas.es_paquete`/`descuento_paquete_pct` los escribe este módulo al confirmar |

---

## Fases de implementación

### Fase 0 — ~~Bloqueada hasta que `reserva_items` exista~~
**Estado:** ✅ Resuelto 2026-07-19 — `reserva_items` existe (Reservas 1.4, dual-write).

### Fase 1 — Construcción de paquete (RF-PAQ-001, 003, 005)
**Estado:** ✅ Hecho 2026-07-19. Acepta IDs de producto directos (sin pantalla de selección real en las otras verticales todavía).
**Entregable:** `router_construccion.py`, `paquete_service.py`.

### Fase 2 — Resumen y condiciones (RF-PAQ-002, 004)
**Estado:** ✅ Hecho 2026-07-19. `tipos_paquete_descuento` sembrado con 4 combinaciones reales (`scripts/seed_tipos_paquete_descuento.py`) — CU-T14/Táctico sigue sin UI de edición.
**Entregable:** `router_resumen.py`.

---

## Complexity Tracking

*No aplica.*
