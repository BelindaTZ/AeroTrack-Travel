# Plan de Implementación — Carrito

**Módulo:** Carrito
**Prefijo:** CAR
**Spec:** [`carrito-spec.md`](./carrito-spec.md)
**Código fuente:** `app/carrito/` *(implementado y probado 2026-07-19)*
**Fecha:** 2026-07-18 (implementado 2026-07-19)
**Estado:** ✅ Implementado y probado — Fase 1+2 completas, 10/10 tests. `reserva_items` ya existe (Reservas 1.4), checkout real verificado.

---

## Resumen

Acumular ítems de cualquier vertical de producto (vuelo, hotel, auto, actividad o crucero) en un carrito por pasajero, con revalidación de precio en el checkout y conversión 1:1 a `reserva_items` al confirmar. Cubre 4 RF y 4 RN sobre 4 CU (CU-O93–O96). Dueño de `carritos`/`carrito_items` — mismo patrón polimórfico que `reserva_items`, a propósito, para que la conversión sea un mapeo directo.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2, design system v4; sin cliente HTTP externo. **Almacenamiento:** PocketBase — dueño de `carritos`, `carrito_items`. **Restricciones:** RN-CAR-001 (revalidación obligatoria de precio en checkout, REG-G2); RN-CAR-002 (un carrito activo por pasajero).

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-G2 (transparencia de precio) | Sí | RF-CAR-004 revalida antes de cobrar |
| REG-B4 (auditoría) | Sí | Toda mutación audita |
| REG-J11 (feedback inmediato) | Sí | Eliminar ítem actualiza el total sin recargar toda la página |

Sin violaciones.

---

## Estructura del proyecto

```text
app/carrito/
├── __init__.py
├── router_carrito.py       # RF-CAR-001,002,003
├── router_checkout.py      # RF-CAR-004
├── schemas.py
├── services/
│   └── carrito_service.py   # RN-CAR-002 (un carrito activo), conversión a reserva_items
├── repositories/
│   └── carrito_repo.py
├── templates/
│   └── ver_carrito.html
└── tests/
    ├── test_carrito.py
    └── test_checkout.py
```

---

## Modelo de datos (resumen)

| Entidad | Rol | Validaciones clave |
|---|---|---|
| `carritos` | Header del carrito | `estado` (activo/convertido/abandonado) es insumo directo de CU-T26/T27 |
| `carrito_items` | Polimórfico, mismo patrón que `reserva_items` | `precio_snapshot` se revalida siempre en checkout (RN-CAR-001) |

---

## Fases de implementación

### Fase 1 — Ver, agregar y eliminar ítems (RF-CAR-001, 002, 003)
**Estado:** ✅ Hecho 2026-07-19. Acepta IDs de producto directos (no hay pantalla de selección real en Hoteles/Autos/Actividades/Cruceros todavía).
**Entregable:** `router_carrito.py`, `carrito_service.py` (crea/reutiliza el carrito activo del pasajero).

### Fase 2 — Checkout (RF-CAR-004)
**Estado:** ✅ Hecho 2026-07-19 — `reserva_items` ya existe (Reservas 1.4).
**Entregable:** `router_checkout.py`, con la revalidación de precio y el mapeo `carrito_items`→`reserva_items` (usando precio vigente, no el snapshot).

---

## Complexity Tracking

*No aplica.*
